import pandas as pd
import os
from sqlalchemy import create_engine
import logging
import time

logging.basicConfig(
    filename="logs/ingestion_db.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)

engine = create_engine('sqlite:///inventory.db')

def ingest_db(df, table_name, engine):
    '''this function will ingest the dataframe into database table'''
    df.to_sql(
        table_name,
        con=engine,
        if_exists='append',
        index=False,
        chunksize=10000
    )
def load_raw_data():
    '''this function will load the CSVs as dataframe and ingest into db'''
    start = time.time()
    for file in os.listdir('data'):
        if file.endswith('.csv'):
            print(f"Processing: {file}")
            for chunk in pd.read_csv('data/' + file, chunksize=50000):
                logging.info(f'Ingesting {file} in db')
                ingest_db(chunk, file[:-4], engine)
    end = time.time()
    total_time = (end - start)/60
    logging.info('Ingestion Complete')
    logging.info(f'\n Total Time Taken: {total_time} minutes')

if __name__ == '__main__':
    load_raw_data()