import re
import unicodedata
import polars as pl

# ==========
# 0) 入力想定
# ----------
# df_text:  本文データフレーム  (columns=["id_src", "text"])
# df_rules: 条件テーブル        (columns=["id", "expr"]) 
#   - expr例: "(PC AND 販売) OR (PC AND 通販)"
#   - 行順が優先順位
# ==========
df_text = pl.DataFrame({"id_src":[1,2], "text":["スマホ限定販売です", "PCが店舗で販売中です。"]})
df_rules = pl.DataFrame({"id":[101,102],
                         "expr":["(PC AND 販売) OR (PC AND 通販)", "((スマホ AND 限定) AND 販売 ) AND です"]})
# 1) 本文の正規化（NFKC→大文字）
#   - Polarsに str.normalize がある場合はそちらを優先（新しめのバージョン）。
#   - ない場合はフォールバックで Python の unicodedata.normalize を使用。
def _normalize_py(s: str) -> str:
    if s is None:
        return s
    return unicodedata.normalize("NFKC", s).upper()

try:
    # 利用可能ならPolars組み込みの正規化＋大文字化（高速）
    # ※ dev以降で `str.normalize('NFKC')` が利用可能
    df_text = df_text.with_columns(
        pl.col("text")
        .str.normalize("NFKC")  # 利用不可な場合は except にフォールバック
        .str.to_uppercase()
        .alias("text_norm")
    )
except Exception:
    # フォールバック（UDF）。必要ならロード時に前処理しておくとより高速化可能。
    df_text = df_text.with_columns(
        pl.col("text").map_elements(_normalize_py, return_dtype=pl.Utf8).alias("text_norm")
    )

# 2) ルール中の“語”を抽出（大文字・NFKC化して揃える）
def normalize_token(t: str) -> str:
    return unicodedata.normalize("NFKC", t).upper()

# トークナイザ（AND/OR/NOT/括弧 以外は「語」とみなす）
TOK_RE = re.compile(r"\s*(\(|\)|AND|OR|NOT|[^()\s]+)\s*")

def tokenize(expr: str):
    return [m.group(1) for m in TOK_RE.finditer(expr)]

# ルールごとのトークン取得＆語集合の収集
all_terms = set()
rules = []  # [(rule_id, tokens_normalized)]
for rid, expr in zip(df_rules["id"].to_list(), df_rules["expr"].to_list()):
    toks = tokenize(expr)
    norm_toks = []
    for t in toks:
        if t in ("AND", "OR", "NOT", "(", ")"):
            norm_toks.append(t)
        else:
            nt = normalize_token(t)
            norm_toks.append(nt)
            all_terms.add(nt)
    rules.append((rid, norm_toks))

# 3) “語”→包含マスク列を一度だけ生成（literal=True でリテラル検索）
#    200語程度なら200列のboolを持っても実メモリは許容範囲（再利用で高速）
def term_col(term: str) -> str:
    # 列名衝突を避けるためハッシュ利用
    return f"__t_{abs(hash(term))}"

mask_exprs = [
    pl.col("text_norm").str.contains(term, literal=True).alias(term_col(term))
    for term in all_terms
]
df = df_text.with_columns(mask_exprs)

# 4) Shunting-yard で RPN へ。NOT > AND > OR の優先順位、右結合は NOT のみ
precedence = {"NOT": 3, "AND": 2, "OR": 1}
right_assoc = {"NOT"}

def to_rpn(tokens):
    out = []
    op = []
    for tok in tokens:
        if tok == "(":
            op.append(tok)
        elif tok == ")":
            while op and op[-1] != "(":
                out.append(op.pop())
            op.pop()  # "(" を捨てる
        elif tok in ("AND", "OR", "NOT"):
            while op and op[-1] != "(" and (
                (precedence[op[-1]] > precedence[tok]) or
                (precedence[op[-1]] == precedence[tok] and tok not in right_assoc)
            ):
                out.append(op.pop())
            op.append(tok)
        else:
            out.append(tok)  # 語
    while op:
        out.append(op.pop())
    return out

# 5) RPN を Polars Expr に変換（語→事前に作ったbool列）
def rpn_to_expr(rpn):
    stack = []
    for tok in rpn:
        if tok == "NOT":
            a = stack.pop()
            stack.append(~a)
        elif tok == "AND":
            b = stack.pop()
            a = stack.pop()
            stack.append(a & b)
        elif tok == "OR":
            b = stack.pop()
            a = stack.pop()
            stack.append(a | b)
        else:
            # 語トークン → 事前計算したマスク列参照
            stack.append(pl.col(term_col(tok)))
    assert len(stack) == 1
    return stack[0]



rule_exprs = [(rid, rpn_to_expr(to_rpn(toks))) for rid, toks in rules]

# 6) 「上から順に見て最初に合致した id を付与」
#    acc がまだ null で、当該ルールが True のときだけ id を入れる
acc = pl.lit(None, dtype=pl.Int64)
for rid, cond in rule_exprs:
    acc = pl.when(acc.is_null() & cond).then(pl.lit(int(rid))).otherwise(acc)

df_out = df.with_columns(acc.alias("matched_id")).select("id_src", "text", "matched_id")

# ====== 例: 動作確認 ======

# → 1行目はルール2に一致（スマホ/限定/販売）、2行目はルール1に一致（PC/販売）
