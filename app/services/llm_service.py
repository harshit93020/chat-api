import google.generativeai as genai
from typing import List, Dict, Optional
from app.config import settings
from app.models.chat import ChatMessage, ConversationModel

class LLMService:
    def __init__(self):
        # Configure the Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    async def generate_conversation_summary(
        self, 
        conversation_id: str, 
        database_service, 
        num_messages: Optional[int] = 100
    ) -> Dict:
        """
        Generate a comprehensive summary for a conversation
        """
        try:
            # Retrieve conversation from database
            conversation = await database_service.get_conversation_by_id(conversation_id)
            
            if not conversation:
                raise ValueError("Conversation not found")
            
            # Sort and limit messages
            messages = conversation.get('messages', [])
            messages = sorted(messages, key=lambda x: x.get('timestamp', None), reverse=True)
            messages = messages[:num_messages]
            
            # Prepare messages for summarization
            formatted_messages = "\n".join([
                f"{msg['sender']['username']}: {msg['content']}" 
                for msg in messages
            ])
            
            # Generate summary using Gemini
            prompt = f"""
            Provide a comprehensive summary of the following conversation:
            
            Conversation Context:
            - Conversation Type: {conversation.get('conversation_type', 'Unknown')}
            - Total Messages: {len(messages)}
            
            Conversation Transcript:
            {formatted_messages}
            
            Summary should include:
            1. Key discussion points
            2. Overall sentiment
            3. Important decisions or outcomes
            4. Participant engagement summary
            """
            
            response = await self.model.generate_content_async(prompt)
            
            # Generate additional insights
            insights_prompt = f"""
            Analyze the conversation and provide structured insights:
            - Sentiment Analysis
            - Communication Patterns
            - Key Keywords
            - Emotional Tone
            
            Conversation Transcript:
            {formatted_messages}
            """
            
            insights_response = await self.model.generate_content_async(insights_prompt)
            
            return {
                "summary": response.text,
                "insights": {
                    "detailed_insights": insights_response.text
                },
                "metadata": {
                    "total_messages": len(messages),
                    "participants": [
                        msg['sender']['username'] for msg in messages
                    ]
                }
            }
        
        except Exception as e:
            # Comprehensive error handling
            return {
                "error": str(e),
                "summary": "Unable to generate summary",
                "insights": {}
            }
    
    async def filter_conversations(
        self, 
        database_service, 
        filters: Dict
    ):
        """
        Advanced conversation filtering with LLM-powered keyword extraction
        """
        try:
            # Basic filtering parameters
            query = {}
            
            # User-based filtering
            if filters.get('user_id'):
                query['participants.user_id'] = filters['user_id']
            
            # Date range filtering
            if filters.get('start_date') and filters.get('end_date'):
                query['created_at'] = {
                    '$gte': filters['start_date'],
                    '$lte': filters['end_date']
                }
            
            # Keyword-based filtering
            if filters.get('keywords'):
                query['$or'] = [
                    {'messages.content': {'$regex': keyword, '$options': 'i'}} 
                    for keyword in filters['keywords']
                ]
            
            # Conversation type filtering
            if filters.get('conversation_type'):
                query['conversation_type'] = filters['conversation_type']
            
            # Perform database query
            conversations = await database_service.conversations_collection.find(query).to_list(length=None)
            
            return conversations
        
        except Exception as e:
            return {
                "error": str(e),
                "filtered_conversations": []
            }

llm_service = LLMService()