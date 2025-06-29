import logging
#from os import name
import os
#import sys
import datetime
from pymongo import MongoClient
#sys.path.append(os.path.abspath("/root/gitlab/genie-ai/shared"))

class StepLogger():
    def __init__(self, process_id: str, db_url: str =None, type: str ='db', db_name: str ="training", collection_name: str ="steplogs"):
        if type and type=='db' and not db_url:
            mongo_url = os.environ['DB_URL']
        else: 
            mongo_url = db_url
        self.process_id = process_id
        self.client = MongoClient(f"mongodb://{mongo_url}:27017")
        self.collection = self.client[db_name][collection_name]
    

    def init_status(self):
        doc = {
            "_id": self.process_id,
            "status": "RUNNING",
            "model_location": None,
            "steps": {
                "prepare_files": {"start": None, "end": None},
                "finetune_model": {"start": None, "end": None},
                "update_card_file": {"start": None, "end": None},
                "upload_to_huggingface": {"start": None, "end": None}
            }
        }
        self.collection.replace_one({"_id": self.process_id}, doc, upsert=True)

    def mark_start(self, step_name: str):
        self.collection.update_one(
            {"_id": self.process_id},
            {"$set": {f"steps.{step_name}.start": datetime.datetime.utcnow()}}
        )

    def mark_end(self, step_name: str):
        self.collection.update_one(
            {"_id": self.process_id},
            {"$set": {f"steps.{step_name}.end": datetime.datetime.utcnow()}}
        )

    def update_document(self, key: str, value: str):
        self.collection.update_one(
            {"_id": self.process_id},
            {"$set": {f"{key}": f"{value}"}}
        )

    def get_status(self):
        return self.collection.find_one({"_id": self.process_id})

class LogDBHandler(logging.Handler):
    '''
    Customized logging handler that puts logs to the database.
    mongo required
    '''
    def __init__(self, db_url: str, collection_name: str, process_id: str, type: str ='db', db_name: str ="training", logger_name: str = None):
        logging.Handler.__init__(self)
        if type and type=='db' and not db_url:
            mongo_url = os.environ['DB_URL']
        else: 
            mongo_url = db_url
        client = MongoClient(f"mongodb://{mongo_url}:27017")
        self.collection = client[db_name][collection_name]
        self.process_id = process_id
        
    def emit(self, record):
        print('inserting data to DB')
        log_doc = {
            "level": record.levelname,
            "message": record.getMessage(),
            "timestamp": datetime.datetime.utcnow(),
            "module": record.module,
            "filename": record.filename,
            "funcName": record.funcName,
            "line": record.lineno,
        }
        ld = {
          "_id": self.process_id,
          "steps": {
            "prepare_files": {
                "start": None,
                "end": None
            },
            "finetune_model": {
                "start": None,
                "end": None
            },
            "update_card_file": {
                "start": None,
                "end": None
            },
            "upload_to_huggingface": {
                "start": None,
                "end": None
            }
        }
        }
        """ A new DB named training will be created for each training run 
        the logging records will go into a collection named "logs" that will be dropped and recreated
        for each one of the trainings we run
        in addition, we want a collection named 'stats' that will initialize a document with _id that will
        be sent from the BE named process_id, and for each step that starts or ends we will update that document
        prepare files
        finetune model
        update card file
        upload to huggingface
        The docuemnt will have:
        _id: process_id
        steps: {
            "prepare_files": {
                "start": None,
                "end": None
            },
            "finetune_model": {
                "start": None,
                "end": None
            },
            "update_card_file": {
                "start": None,
                "end": None
            },
            "upload_to_huggingface": {
                "start": None,
                "end": None
            }
        }
        so this function will check if the logs has a start or end flag, and if so, update the start/end for
        the relevant step
        """
        self.collection.insert_one(log_doc)

    def log_to_db(self , message):
        self.collection.insert_one({"name": message})


def setup_mongo_logger(name, db_url, db_name, collection_name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    mongo_handler = LogDBHandler(db_url, db_name, collection_name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    mongo_handler.setFormatter(formatter)
    logger.addHandler(mongo_handler)
    return logger