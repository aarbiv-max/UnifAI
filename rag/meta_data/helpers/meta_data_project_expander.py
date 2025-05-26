from collections import defaultdict
from rag.be_utils.db.db import mongo, Collections, db
from rag.be_utils.utils import time_execution
from .metadata_extractor.meta_data_extractor import MetaDataExtractorBase
from .metadata_extractor.kubevirt_meta_data_extractor import KubevirtMetaDataExtractor
from .metadata_extractor.eco_go_meta_data_extractor import EcogoMetaDataExtractor
from .metadata_extractor.oadp_meta_data_extractor import OadpMetaDataExtractor

class MetaDataProjectExpander:
    def __init__(self, parsed_elements, project_name, project_repo_path, naming_mapping = {}, built_in_keys = [], exclude_types = [], project_programming_languages = []):
        self.parsed_elements = parsed_elements
        self.project_name = project_name
        self.project_repo_path = project_repo_path
        self.naming_mapping = naming_mapping 
        self.built_in_keys = built_in_keys
        self.exclude_types = exclude_types 
        self.project_programming_languages = project_programming_languages
        self.required_parsed_elements = [
            {**ele, "git_repo_link": self.project_repo_path}
            for ele in self.parsed_elements
            if ele["element_type"] not in self.exclude_types
        ]
        # Registeration of different extractors expected to be handled from __init__ file of the MetaDataExtractor class
        MetaDataExtractorBase.register_extractor("kubevirt", KubevirtMetaDataExtractor)
        MetaDataExtractorBase.register_extractor("eco-gotests", EcogoMetaDataExtractor)
        MetaDataExtractorBase.register_extractor("oadp", OadpMetaDataExtractor)

    @time_execution
    def add_metadata(self):
        """
        Add metadata to each object in the parsed objects list, with error handling per element.
        """
        for element in self.required_parsed_elements:
            try:
                metadata = defaultdict(list)
                for key in self.built_in_keys:
                    metadata[self.naming_mapping.get(key, key)] = element.get(key, "")
                element_name = element.get("name", "")
                element_code = element.get("code", "")
                extractor = MetaDataExtractorBase.create_extractor(self.project_name)

                combined_text = f"{element_name} {element_code}"
                metadata["action"] = extractor.extract_actions(combined_text)
                metadata["buzz_words"] = extractor.extract_buzz_words(element_code)

                if self.project_name == "kubevirt":
                    metadata["k8s_terms"] = extractor.extract_k8s_terms(combined_text)

                element["metadata"] = dict(metadata)

            except Exception as e:
                print(f"[MetaDataProjectExpander] Failed to extract metadata for element: {element.get('name', '[unknown]')} — {e}")


    @mongo
    def add_to_db(self):
        """
        Add parsed objects to the database with error handling.
        If an existing document with the same 'file_location', 'name' and 'element_type' is found,
        it will be replaced, otherwise a new document will be inserted.
        """
        try:
            collection = Collections.by_name('parsed_objects')
            
            # Loop through each parsed element and perform upsert
            for element in self.required_parsed_elements:
                # Define the filter (existing document check)
                filter = {
                    'file_location': element['file_location'],
                    'element_type': element['element_type'],
                    "name": element.get("name", "")
                }
                
                # Perform upsert: If document exists, it will be replaced, otherwise inserted
                result = collection.update_one(
                    filter, 
                    {'$set': element},  # Replace the existing document with the new one
                    upsert=True  # If no document matches the filter, a new one will be inserted
                )
                if result.upserted_id:
                    print(f"[MetaDataProjectExpander] Inserted new document with _id: {result.upserted_id}")
                else:
                    print(f"[MetaDataProjectExpander] Updated existing document with filter {filter}")

            return "Operation successful"

        except Exception as e:
            print(f"[MetaDataProjectExpander] Failed to process parsed elements: {e}")
            return None
