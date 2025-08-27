from django.core.management.base import BaseCommand
from django.db import IntegrityError
import yfinance as yf

from blog.models import StockHistory  

class Command(BaseCommand):
    help = 'Fetches historical stock data from Yahoo Finance and stores it in the DB'

    def add_arguments(self, parser):
        parser.add_argument('ticker', type=str, help='Stock ticker symbol (e.g., AAPL)')
        parser.add_argument('--period', type=str, default='1y', help='Period to fetch (e.g., 1mo, 1y, max)')

    def handle(self, *args, **options):
        ticker_symbol = options['ticker']
        period = options['period']

        self.stdout.write(f"Fetching data for {ticker_symbol} over {period}...")

        try:
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(period=period)

            if data.empty:
                self.stdout.write(self.style.ERROR("No data fetched. Check ticker symbol or period."))
                return

            data.reset_index(inplace=True)
            data['Date'] = data['Date'].dt.date 

            saved_count = 0
            for index, row in data.iterrows():
                try:
                    StockHistory.objects.create(
                        ticker=ticker_symbol.upper(),
                        date=row['Date'],
                        open_price=row['Open'],
                        high_price=row['High'],
                        low_price=row['Low'],
                        close_price=row['Close'],
                        volume=row['Volume']
                    )
                    saved_count += 1
                except IntegrityError:
                    pass
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error saving row: {e}"))

            self.stdout.write(self.style.SUCCESS(f"Successfully saved {saved_count} records for {ticker_symbol}."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching data: {e}"))