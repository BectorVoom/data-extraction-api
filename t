#!/usr/bin/env python3
"""
Functional Polars-based tagging pipeline that assigns tags to DataFrame rows
by matching text against regex patterns from a CSV file.

Implements functional programming principles with pure functions and immutable transformations.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Pattern
import polars as pl


def load_patterns(csv_path: str) -> pl.DataFrame:
    """
    Load tag patterns from CSV file with comprehensive error handling.
    
    Args:
        csv_path: Path to the patterns CSV file
        
    Returns:
        DataFrame with 'tag' and 'pattern' columns
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        Exception: For other CSV reading errors
    """
    try:
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"Patterns file not found: {csv_path}")
        
        df = pl.read_csv(csv_path)
        
        # Validate required columns
        required_cols = {'tag', 'pattern'}
        if not required_cols.issubset(set(df.columns)):
            raise ValueError(f"CSV must contain columns: {required_cols}")
        
        # Filter out empty patterns
        df = df.filter(pl.col('pattern').is_not_null() & (pl.col('pattern') != ''))
        
        print(f"✅ Loaded {len(df)} patterns from {csv_path}")
        return df
        
    except Exception as e:
        print(f"❌ Error loading patterns from {csv_path}: {e}")
        raise


def compile_patterns_by_tag(patterns_df: pl.DataFrame) -> Dict[str, List[Pattern[str]]]:
    """
    Compile regex patterns grouped by tag with Unicode support and error handling.
    
    Args:
        patterns_df: DataFrame with 'tag' and 'pattern' columns
        
    Returns:
        Dictionary mapping tag names to lists of compiled regex patterns
    """
    compiled_patterns: Dict[str, List[Pattern[str]]] = {}
    compilation_errors: List[str] = []
    
    # Group patterns by tag and compile them
    for row in patterns_df.iter_rows(named=True):
        tag = row['tag']
        pattern_str = row['pattern']
        
        try:
            # Unicode-aware regex compilation for Japanese text support
            compiled_pattern = re.compile(pattern_str, re.UNICODE | re.DOTALL)
            
            if tag not in compiled_patterns:
                compiled_patterns[tag] = []
            compiled_patterns[tag].append(compiled_pattern)
            
        except re.error as e:
            error_msg = f"Invalid regex pattern '{pattern_str}' for tag '{tag}': {e}"
            compilation_errors.append(error_msg)
            print(f"⚠️  {error_msg}")
    
    if compilation_errors:
        print(f"⚠️  {len(compilation_errors)} regex compilation errors occurred")
        for error in compilation_errors:
            print(f"   - {error}")
    
    print(f"✅ Compiled patterns for {len(compiled_patterns)} tags")
    return compiled_patterns


def create_sample_data() -> pl.DataFrame:
    """
    Create sample DataFrame with test cases for all required pattern types.
    
    Returns:
        DataFrame with 'text' column containing test cases
    """
    # Sample data covering all required patterns plus negative examples
    sample_texts = [
        # SK30 pattern matches
        "申請書類はSK30を参考にしてください",
        "SK30の提出が必要です",
        
        # 就職.*(前|活動|活動中) pattern matches  
        "就職の前に準備が大切です",
        "就職活動を始めました",
        "現在就職活動中です",
        "就職に向けて活動しています",
        
        # 就職.*時 pattern matches
        "就職時の注意点について",
        "就職した時のことを考える",
        
        # S\d{3} pattern matches (S followed by exactly 3 digits)
        "申請コードS123で処理します",
        "S456の案件について", 
        "S789を確認してください",
        
        # Multiple matches (should get multiple tags)
        "就職前の準備とSK30について", # Should match both 就活前 patterns
        "S999の就職活動について",      # Should match both 就活前 patterns
        
        # Additional tag matches (内定後, 技術)
        "内定後の手続きについて",
        "採用後のフォローアップ",
        "プログラミングスキルが必要",
        "エンジニアとして開発業務",
        
        # Negative examples (should not match any pattern)
        "一般的な情報です",
        "特に関係のない文章",
        "S12は短すぎる", # S followed by only 2 digits
        "SK29は違う番号", # SK29 not SK30
        "就職以外の話題", # 就職 but no matching suffix
    ]
    
    df = pl.DataFrame({"text": sample_texts})
    print(f"✅ Created sample DataFrame with {len(df)} test cases")
    return df


def apply_tag_matching(text_df: pl.DataFrame, compiled_patterns: Dict[str, List[Pattern[str]]]) -> pl.DataFrame:
    """
    Apply tag matching to text DataFrame using functional approach.
    
    Args:
        text_df: DataFrame with 'text' column
        compiled_patterns: Dictionary of compiled regex patterns by tag
        
    Returns:
        DataFrame with additional 'tags' column containing list of matched tags
    """
    def match_text_to_tags(text: str) -> List[str]:
        """Pure function to match a single text against all patterns."""
        matched_tags = []
        
        for tag, patterns in compiled_patterns.items():
            # If any pattern for this tag matches, add the tag
            if any(pattern.search(text) for pattern in patterns):
                matched_tags.append(tag)
        
        return matched_tags
    
    # Apply tag matching using Polars' functional API
    result_df = text_df.with_columns([
        pl.col("text").map_elements(
            match_text_to_tags,
            return_dtype=pl.List(pl.Utf8)
        ).alias("tags")
    ])
    
    print(f"✅ Applied tag matching to {len(result_df)} rows")
    return result_df


def create_expected_test_results() -> Dict[str, List[str]]:
    """
    Define expected tag assignments for validation.
    
    Returns:
        Dictionary mapping text patterns to expected tag lists
    """
    return {
        # SK30 matches
        "申請書類はSK30を参考にしてください": ["就活前"],
        "SK30の提出が必要です": ["就活前"],
        
        # 就職.*(前|活動|活動中) matches
        "就職の前に準備が大切です": ["就活前"],
        "就職活動を始めました": ["就活前"],
        "現在就職活動中です": ["就活前"],
        "就職に向けて活動しています": ["就活前"],
        
        # 就職.*時 matches
        "就職時の注意点について": ["就活前"],
        "就職した時のことを考える": ["就活前"],
        
        # S\d{3} matches
        "申請コードS123で処理します": ["就活前"],
        "S456の案件について": ["就活前"],
        "S789を確認してください": ["就活前"],
        
        # Multiple matches
        "就職前の準備とSK30について": ["就活前"],  # Multiple patterns, same tag
        "S999の就職活動について": ["就活前"],      # Multiple patterns, same tag
        
        # Other tag matches
        "内定後の手続きについて": ["内定後"],
        "採用後のフォローアップ": ["内定後"],
        "プログラミングスキルが必要": ["技術"],
        "エンジニアとして開発業務": ["技術"],
        
        # Negative examples
        "一般的な情報です": [],
        "特に関係のない文章": [],
        "S12は短すぎる": [],
        "SK29は違う番号": [],
        "就職以外の話題": [],
    }


def validate_results(result_df: pl.DataFrame) -> bool:
    """
    Validate tagging results against expected outcomes.
    
    Args:
        result_df: DataFrame with 'text' and 'tags' columns
        
    Returns:
        True if all validations pass, False otherwise
    """
    expected_results = create_expected_test_results()
    validation_errors = []
    
    print("\n🔍 Running validation tests...")
    
    for row in result_df.iter_rows(named=True):
        text = row['text']
        actual_tags = sorted(row['tags']) if row['tags'] else []
        expected_tags = sorted(expected_results.get(text, []))
        
        if actual_tags != expected_tags:
            validation_errors.append({
                'text': text,
                'expected': expected_tags,
                'actual': actual_tags
            })
    
    if validation_errors:
        print(f"❌ {len(validation_errors)} validation errors found:")
        for error in validation_errors:
            print(f"   Text: '{error['text'][:50]}{'...' if len(error['text']) > 50 else ''}'")
            print(f"   Expected: {error['expected']}")
            print(f"   Actual: {error['actual']}")
        return False
    else:
        print(f"✅ All {len(result_df)} test cases passed validation")
        return True


def run_pipeline() -> bool:
    """
    Execute the complete functional tagging pipeline.
    
    Returns:
        True if pipeline completes successfully with all tests passing
    """
    try:
        print("🚀 Starting Functional Polars Tagging Pipeline\n")
        
        # Step 1: Load and display patterns
        print("📋 Step 1: Loading tag patterns...")
        patterns_df = load_patterns("patterns.csv")
        print("\n📋 Patterns CSV contents:")
        print(patterns_df)
        
        # Step 2: Compile patterns by tag
        print(f"\n⚙️  Step 2: Compiling regex patterns...")
        compiled_patterns = compile_patterns_by_tag(patterns_df)
        
        # Step 3: Create sample data
        print(f"\n📊 Step 3: Creating sample input data...")
        sample_df = create_sample_data()
        print("\n📊 Sample input DataFrame:")
        print(sample_df)
        
        # Step 4: Apply tag matching
        print(f"\n🏷️  Step 4: Applying tag matching...")
        result_df = apply_tag_matching(sample_df, compiled_patterns)
        print("\n🏷️  Results with tags:")
        print(result_df)
        
        # Step 5: Validate results
        print(f"\n✅ Step 5: Validating results...")
        validation_passed = validate_results(result_df)
        
        if validation_passed:
            print(f"\n🎉 ALL TESTS PASSED - Pipeline completed successfully!")
            return True
        else:
            print(f"\n❌ Some tests failed - Please check implementation")
            return False
            
    except Exception as e:
        print(f"\n💥 Pipeline failed with error: {e}")
        return False


def main():
    """Main entry point with error handling."""
    try:
        success = run_pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚡ Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
