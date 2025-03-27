from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from bson import ObjectId
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from app.config import settings

class DatabaseService:
    def __init__(self, mongo_uri: str, database_name: str):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[database_name]
        self.conversations_collection = self.db['conversations']
        self.users_collection = self.db['users']

    def _serialize_mongodb_obj(self, obj: Any) -> Any:
        """Convert MongoDB objects to JSON-serializable format"""
        if isinstance(obj, dict):
            return {
                key: self._serialize_mongodb_obj(value) 
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self._serialize_mongodb_obj(item) for item in obj]
        elif isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    async def create_indexes(self):
        """
        Create efficient indexes for fast querying
        """
        await self.conversations_collection.create_indexes([
            IndexModel([('participants.user_id', ASCENDING)]),
            IndexModel([('last_message_timestamp', DESCENDING)]),
            IndexModel([('conversation_type', ASCENDING)]),
            IndexModel([('created_at', DESCENDING)]),
            IndexModel([('tags', ASCENDING)])
        ])

    async def advanced_conversation_search(
        self, 
        filters: Dict, 
        page: int = 1, 
        page_size: int = 10
    ):
        """
        Advanced search with efficient pagination and filtering
        """
        query = {}
        
        # User participation filter
        if filters.get('user_id'):
            query['participants.user_id'] = filters['user_id']
        
        # Date range filter
        if filters.get('start_date') and filters.get('end_date'):
            query['created_at'] = {
                '$gte': filters['start_date'],
                '$lte': filters['end_date']
            }
        
        # Conversation type filter
        if filters.get('conversation_type'):
            query['conversation_type'] = filters['conversation_type']
        
        # Tags filter
        if filters.get('tags'):
            query['tags'] = {'$in': filters['tags']}
        
        # Keyword search in messages
        if filters.get('keywords'):
            query['$or'] = [
                {'messages.content': {'$regex': keyword, '$options': 'i'}} 
                for keyword in filters['keywords']
            ]
        
        # Efficient aggregation pipeline for search and pagination
        pipeline = [
            {'$match': query},
            {'$sort': {'last_message_timestamp': -1}},
            {'$skip': (page - 1) * page_size},
            {'$limit': page_size},
            {
                '$project': {
                    'conversation_id': '$_id',
                    'participants': 1,
                    'conversation_type': 1,
                    'last_message_timestamp': 1,
                    'messages_count': {'$size': '$messages'}
                }
            }
        ]
        
        results = await self.conversations_collection.aggregate(pipeline).to_list(length=None)
        total_count = await self.conversations_collection.count_documents(query)
        
        return {
            'conversations': self._serialize_mongodb_obj(results),
            'total_count': total_count,
            'page': page,
            'page_size': page_size
        }
    
    async def start_conversation(self, conversation_data: Dict) -> str:
        """Start a new conversation"""
        # Convert Pydantic model to dict if needed
        if hasattr(conversation_data, 'dict'):
            conversation_data = conversation_data.dict()

        # Add timestamps
        now = datetime.utcnow()
        conversation_data['created_at'] = now
        conversation_data['updated_at'] = now
        conversation_data['last_message_timestamp'] = now

        # Ensure messages array exists
        if 'messages' not in conversation_data:
            conversation_data['messages'] = []

        # Insert conversation
        result = await self.conversations_collection.insert_one(conversation_data)
        return str(result.inserted_id)

    async def add_message_to_conversation(
        self,
        conversation_id: str,
        message: Dict
    ) -> bool:
        """Add a message to an existing conversation"""
        try:
            # Convert message to dict if it's a Pydantic model
            if hasattr(message, 'dict'):
                message = message.dict()

            # Add timestamp if not present
            if 'timestamp' not in message:
                message['timestamp'] = datetime.utcnow()

            # Update conversation with new message
            result = await self.conversations_collection.update_one(
                {'_id': ObjectId(conversation_id)},
                {
                    '$push': {'messages': message},
                    '$set': {
                        'updated_at': datetime.utcnow(),
                        'last_message_timestamp': message['timestamp']
                    }
                }
            )

            return result.modified_count > 0

        except Exception as e:
            print(f"Error adding message to conversation: {e}")
            return False

    async def get_conversation_by_id(
        self,
        conversation_id: str
    ) -> Optional[Dict]:
        """Retrieve a conversation by ID"""
        try:
            conversation = await self.conversations_collection.find_one(
                {'_id': ObjectId(conversation_id)}
            )
            return self._serialize_mongodb_obj(conversation)
        except Exception as e:
            print(f"Error retrieving conversation: {e}")
            return None

    async def get_user_conversations(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 10
    ) -> Dict:
        """Get conversations for a specific user"""
        try:
            skip = (page - 1) * limit
            query = {'participants.user_id': user_id}
            
            conversations = await self.conversations_collection.find(query) \
                .sort('last_message_timestamp', DESCENDING) \
                .skip(skip) \
                .limit(limit) \
                .to_list(length=limit)
            
            total_count = await self.conversations_collection.count_documents(query)
            
            return {
                'conversations': self._serialize_mongodb_obj(conversations),
                'total_count': total_count,
                'page': page,
                'limit': limit
            }
        except Exception as e:
            print(f"Error retrieving user conversations: {e}")
            return {
                'conversations': [],
                'total_count': 0,
                'page': page,
                'limit': limit
            }


database_service = DatabaseService(settings.MONGO_URI, settings.DATABASE_NAME)