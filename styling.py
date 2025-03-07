import pandas as pd
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class TrainStyler:
    @staticmethod
    def apply_train_styling(df: pd.DataFrame) -> pd.DataFrame.style:
        """Apply all styling to the train data DataFrame"""
        return df.style.apply(TrainStyler._highlight_delay, axis=None)

    @staticmethod
    def _is_positive_or_plus(value) -> bool:
        """Check if a value is positive or contains a plus sign."""
        if value is None:
            return False
        value_str = str(value).strip()
        if '+' in value_str:
            return True
        try:
            return float(value_str) > 0
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _highlight_delay(data: pd.DataFrame) -> pd.DataFrame:
        """Apply styling to the DataFrame based on delays and train types"""
        styles = pd.DataFrame('', index=data.index, columns=data.columns)

        # Apply red color to positive delays
        if 'Delay' in data.columns:
            styles['Delay'] = data['Delay'].apply(
                lambda x: 'color: red; font-weight: bold' 
                if x and TrainStyler._is_positive_or_plus(x) else '')

        # Style based on train types in FROM-TO column
        from_to_col = 'FROM-TO'
        if from_to_col in data.columns:
            for idx, value in data[from_to_col].items():
                if pd.notna(value):
                    extracted_value = str(value).split(' ')[0].upper()
                    logger.debug(f"FROM-TO value: {value}, extracted: {extracted_value}")

                    font_styles = {
                        'DMU': 'color: blue; font-weight: bold; ',
                        'MEM': 'color: blue; font-weight: bold; ',
                        'SUF': 'color: #e83e8c; font-weight: bold; ',
                        'MEX': 'color: #e83e8c; font-weight: bold; ',
                        'VND': 'color: #e83e8c; font-weight: bold; ',
                        'RJ': 'color: #e83e8c; font-weight: bold; ',
                        'PEX': 'color: #e83e8c; font-weight: bold; ',
                        'TOD': 'color: #fd7e14; font-weight: bold; '
                    }

                    style_to_apply = font_styles.get(extracted_value, '')
                    if style_to_apply:
                        for col in styles.columns:
                            styles.loc[idx, col] += style_to_apply

        # Style based on train numbers
        if 'Train No.' in data.columns:
            for idx, train_no in data['Train No.'].items():
                if pd.notna(train_no):
                    train_no_str = str(train_no).strip()
                    if train_no_str:
                        first_digit = train_no_str[0]
                        logger.debug(f"Train number: {train_no_str}, first digit: {first_digit}")

                        color_style = ''
                        if first_digit == '6':
                            color_style = 'color: blue; font-weight: bold;'
                        elif first_digit in ['1', '2']:
                            color_style = 'color: #e83e8c; font-weight: bold;'
                        elif first_digit == '0':
                            color_style = 'color: #fd7e14; font-weight: bold;'

                        if color_style:
                            for col in styles.columns:
                                styles.loc[idx, col] += color_style

        return styles
