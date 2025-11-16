"""
Portfolio XML generator.
"""

from lxml import etree
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from ..trade_builders import TradeBuilders
from ..validators import TradeValidator


class PortfolioGenerator:
    """
    Generate portfolio.xml from trade data.

    Reads trade DataFrames and generates XML using appropriate trade builders.
    """

    def __init__(self, skip_invalid: bool = True, warn_on_skip: bool = True):
        """
        Initialize portfolio generator.

        Args:
            skip_invalid: Whether to skip invalid trades
            warn_on_skip: Whether to print warnings for skipped trades
        """
        self.skip_invalid = skip_invalid
        self.warn_on_skip = warn_on_skip
        self.skipped_trades: List[Dict] = []
        self.generated_trades: List[str] = []

    def generate(
        self,
        trades: Dict[str, pd.DataFrame]
    ) -> etree.Element:
        """
        Generate portfolio XML from trade DataFrames.

        Args:
            trades: Dictionary of trade DataFrames keyed by trade type

        Returns:
            Portfolio XML element
        """
        # Create root Portfolio element
        portfolio = etree.Element("Portfolio")

        for trade_type, df in trades.items():
            if df is None or df.empty:
                continue

            self._add_trades(
                portfolio,
                df,
                trade_type,
                TradeBuilders[trade_type]
            )
            
        return portfolio

    def _add_trades(
        self,
        portfolio: etree.Element,
        df: pd.DataFrame,
        trade_type: str,
        builder_class
    ) -> None:
        """
        Add trades from DataFrame to portfolio.

        Args:
            portfolio: Portfolio XML element
            df: DataFrame containing trade data
            trade_type: Type of trades (for validation)
            builder_class: Trade builder class to use
        """
        for idx, row in df.iterrows():
            # Convert row to dictionary
            trade_data = row.to_dict()

            # Validate trade
            validation_result = TradeValidator.validate_trade(trade_data, trade_type)

            if not validation_result.is_valid:
                # Trade is invalid
                trade_id = trade_data.get("TradeId", f"Row_{idx}")

                if self.skip_invalid:
                    # Skip this trade
                    self.skipped_trades.append({
                        "trade_id": trade_id,
                        "trade_type": trade_type,
                        "errors": validation_result.errors,
                        "warnings": validation_result.warnings
                    })

                    if self.warn_on_skip:
                        print(f"X  Skipping invalid trade {trade_id}:")
                        for error in validation_result.errors:
                            print(f"   • {error}")
                else:
                    # Raise exception
                    error_msg = f"Invalid trade {trade_id}: " + "; ".join(validation_result.errors)
                    raise ValueError(error_msg)

                continue

            # Show warnings even for valid trades
            if validation_result.warnings and self.warn_on_skip:
                trade_id = trade_data.get("TradeId", f"Row_{idx}")
                print(f"⚡ Warnings for trade {trade_id}:")
                for warning in validation_result.warnings:
                    print(f"   • {warning}")

            # Build trade XML
            try:
                builder = builder_class(trade_data)
                trade_elem = builder.build()
                portfolio.append(trade_elem)
                self.generated_trades.append(trade_data.get("TradeId", f"Row_{idx}"))

            except Exception as e:
                trade_id = trade_data.get("TradeId", f"Row_{idx}")

                if self.skip_invalid:
                    self.skipped_trades.append({
                        "trade_id": trade_id,
                        "trade_type": trade_type,
                        "errors": [str(e)],
                        "warnings": []
                    })

                    if self.warn_on_skip:
                        print(f"X  Skipping trade {trade_id} due to build error: {e}")
                else:
                    raise

    def save_to_file(self, portfolio: etree.Element, output_path: Path) -> None:
        """
        Save portfolio XML to file.

        Args:
            portfolio: Portfolio XML element
            output_path: Path to output file
        """
        tree = etree.ElementTree(portfolio)
        tree.write(
            str(output_path),
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True
        )

    def get_summary(self) -> Dict:
        """
        Get summary of generation process.

        Returns:
            Dictionary with generation statistics
        """
        return {
            "generated_count": len(self.generated_trades),
            "skipped_count": len(self.skipped_trades),
            "generated_trades": self.generated_trades,
            "skipped_trades": self.skipped_trades
        }