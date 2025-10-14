import re
import unicodedata
import polars as pl

# === ユーザー環境に合わせてここだけ設定 ===
TEXT_COLS = ["text_a", "text_b", "text_c"]  # 正規化対象の3列
COND_COLS = ["cond1", "cond2", "cond3", "cond4", "cond5"]  # ルール側の最大5条件列

# どの条件列を df 側のどのテキスト列に当てるか（例）
# cond1→text_a, cond2→text_b, cond3→text_c, cond4→text_a, cond5→text_b
CONDITION_TO_TEXTCOL = {
    "cond1": "text_a",
    "cond2": "text_a",  # ← 修正：cond2 を text_a に
    "cond3": "text_c",
    "cond4": "text_a",
    "cond5": "text_b",
}


# === サンプル入力（実データでは df / rules を読み込む） ===
df = pl.DataFrame({
    "text_a": ["スマホ限定販売", "PCが店舗で販売中です。"],
    "text_b": ["秋葉原", ""],
    "text_c": ["", ""],
})

rules = pl.DataFrame({
    "id": [101, 102],
    # 例: (PC AND 販売) OR (PC AND 通販)
    "cond1": ["(PC AND 販売) OR (PC AND 通販)", None],
    "cond2": [None, "スマホ AND 限定 AND 販売"],
    "cond3": ["秋葉原", None],
    "cond4": [None, None],
    "cond5": [None, None],
})

# === 前処理：正規化（NFKC + upper） ===
def normalize_upper(s: str) -> str:
    if s is None:
        return None
    return unicodedata.normalize("NFKC", s).upper()

# 大文字化は Polars ネイティブでも可能だが、NFKC は Python 側で実施
# 注意: map_elements は UDF なので乱用しない（本処理では初回のみ）
df_norm = df.with_columns([
    pl.col(c).map_elements(normalize_upper, return_dtype=pl.Utf8).alias(c) for c in TEXT_COLS
])

# === トークナイザ：条件式から語と演算子/括弧を抽出 ===
OPS = {"AND", "OR", "NOT", "(", ")"}
TOKEN_RE = re.compile(r"\s*([()])\s*|\s*(AND|OR|NOT)\s*|\s*([^()\s]+)\s*", re.IGNORECASE)

def tokenize(expr: str):
    if not expr:
        return []
    out = []
    for m in TOKEN_RE.finditer(expr):
        paren, op, word = m.groups()
        if paren:
            out.append(paren)
        elif op:
            out.append(op.upper())
        elif word:
            out.append(unicodedata.normalize("NFKC", word).upper())
    return out

# === すべての語（トークン）をユニーク抽出して、列ごとに一括で contains(literal=True) ベクトル化 ===
def collect_unique_terms(rules_df: pl.DataFrame) -> set[str]:
    terms = set()
    for col in COND_COLS:
        if col in rules_df.columns:
            for s in rules_df[col].drop_nulls().to_list():
                for t in tokenize(s):
                    if t not in OPS and t not in ("(", ")"):
                        terms.add(t)
    return terms

TERMS = collect_unique_terms(rules)

# 各テキスト列×語ごとに、再利用可能なブール列名を作る
def term_flag_name(text_col: str, term: str) -> str:
    # 衝突回避のため簡易ハッシュ
    return f"__has__{text_col}__{abs(hash(term))}"

# 一括で with_columns して、文字列探索をベクトル化（リテラル完全一致・部分一致OK）
# Polarsのstr.contains(literal=True) はリテラル検索（正規表現オフ）で高速
new_bool_exprs = []
for col in TEXT_COLS:
    for term in TERMS:
        new_bool_exprs.append(
            pl.col(col).str.contains(pl.lit(term), literal=True).alias(term_flag_name(col, term))
        )

df_flags = df_norm.with_columns(new_bool_exprs)

# === Shunting-Yard で中置 → 逆ポーランド（RPN）へ、RPN から Polars Expr を組み立て ===
PRECEDENCE = {"NOT": 3, "AND": 2, "OR": 1}
ARITY = {"NOT": 1, "AND": 2, "OR": 2}

def to_rpn(tokens: list[str]) -> list[str]:
    out, stack = [], []
    for tok in tokens:
        if tok in OPS:
            if tok == "(":
                stack.append(tok)
            elif tok == ")":
                while stack and stack[-1] != "(":
                    out.append(stack.pop())
                if stack and stack[-1] == "(":
                    stack.pop()
            else:  # operator
                while stack and stack[-1] in PRECEDENCE and PRECEDENCE[stack[-1]] >= PRECEDENCE[tok]:
                    out.append(stack.pop())
                stack.append(tok)
        else:
            out.append(tok)
    while stack:
        out.append(stack.pop())
    return out

def rpn_to_pl_expr(rpn: list[str], text_col: str) -> pl.Expr:
    st: list[pl.Expr] = []
    for tok in rpn:
        if tok in PRECEDENCE:
            if ARITY[tok] == 1:
                a = st.pop()
                st.append(~a)
            else:
                b = st.pop()
                a = st.pop()
                st.append((a & b) if tok == "AND" else (a | b))
        else:
            # 語 → 事前計算済みフラグ列を参照
            st.append(pl.col(term_flag_name(text_col, tok)))
    assert len(st) == 1
    return st[0]

def build_predicate(expr_str: str, target_col: str) -> pl.Expr:
    toks = tokenize(expr_str)
    if not toks:
        # 空なら True（無視したい場合はここを pl.lit(True) / False 切替）
        return pl.lit(True)
    rpn = to_rpn(toks)
    return rpn_to_pl_expr(rpn, target_col)

# === 各ルール行ごとの「合致条件」を作る（複数条件列は AND で束ねる） ===
rule_masks = []
rule_values = []  # then() で返す id 値

for row in rules.iter_rows(named=True):
    rid = row["id"]
    preds = []
    for cond_col in COND_COLS:
        expr = row.get(cond_col)
        if expr:
            tcol = CONDITION_TO_TEXTCOL[cond_col]
            preds.append(build_predicate(expr, tcol))
    # その行に有効な条件が1つもなければスキップ
    if not preds:
        continue
    # 複数条件列は AND
    row_mask = pl.all_horizontal(preds) if len(preds) > 1 else preds[0]
    rule_masks.append(row_mask)
    rule_values.append(pl.lit(rid))

# === 上から順の「最初にマッチした id」を coalesce で決定（first non-null） ===
# when(mask).then(id).otherwise(None) を横に並べ、左から最初の非NULLを採る
id_exprs = [
    pl.when(m).then(v).otherwise(pl.lit(None, dtype=pl.Int64))
    for m, v in zip(rule_masks, rule_values)
]
assigned_id_expr = pl.coalesce(id_exprs).alias("matched_id")

result = df_flags.with_columns(assigned_id_expr).select(TEXT_COLS + ["matched_id"])

print(result)
