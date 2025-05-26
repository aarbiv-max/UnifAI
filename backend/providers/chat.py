from be_utils.db.db import mongo, Collections
@mongo
def get_chat_history(model_id):
    """
    :param str model_id:
    :return List containing chat history:
    """
    try:
        collection = Collections.by_name('chatHistory')
        if not collection:
            raise Exception("Failed to retrieve the collection 'chatHistory'")
        result = collection.find({'modelId': model_id}, {'_id': 0}).sort('latestTimestamp', -1)
        result_list = list(result)  # Convert cursor to list
    except Exception as error:
        print(f"Error fetching chat history: {error}")
        return []
    return result_list

@mongo
def update_current_chat_history(session_id, messages, first_message, model_id):
    """
    Updates the chat history for a given model and session.
    If a chat history exists, it updates it; otherwise, it creates a new record.
    """
    result = Collections.by_name('chatHistory').update_one({"modelId": model_id, "sessionId": session_id},
        {"$set": {"messages": messages}, "$setOnInsert": {"firstMessage": first_message, "modelId": model_id},
        "$currentDate": {"latestTimestamp": True}}, upsert=True)
    return str(result.upserted_id) if result.upserted_id else result.modified_count


@mongo
def delete_session_from_chat_history(session_id):
    """
    This function deletes the chat history of a given session.
    """
    result = Collections.by_name('chatHistory').delete_one({"sessionId": session_id})
    return result.deleted_count

@mongo
def rename_title_of_chat_session(session_id, title):
    """
    This function deletes the chat history of a given session.
    """
    result = Collections.by_name('chatHistory').update_one({"sessionId": session_id}, {"$set": {"title": title}})
    return result.modified_count