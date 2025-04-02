import time
import logging
import uuid
import asyncio
from flask import Blueprint, request, jsonify, current_app, session
from utils.gemini import GeminiChat
from models import db, Chat, Message, Feedback

# Configure logging
logger = logging.getLogger(__name__)

# Initialize chat blueprint
chat_bp = Blueprint('chat', __name__)

# Initialize a dictionary to store chat sessions by session ID
chat_sessions = {}

# Simple rate limiting middleware
def check_rate_limit(client_ip):
    """Check if client has exceeded rate limit"""
    rate_limit_config = current_app.config.get('RATE_LIMIT', {
        'clients': {},
        'window_seconds': 60,
        'max_requests': 10
    })
    clients = rate_limit_config.get('clients', {})
    window = rate_limit_config.get('window_seconds', 60)
    max_requests = rate_limit_config.get('max_requests', 10)
    
    current_time = time.time()
    
    # Initialize client if not exists
    if client_ip not in clients:
        clients[client_ip] = {"requests": [], "blocked_until": 0}
    
    client = clients[client_ip]
    
    # Check if client is currently blocked
    if client["blocked_until"] > current_time:
        return False, client["blocked_until"] - current_time
    
    # Remove requests older than the window
    client["requests"] = [req_time for req_time in client["requests"] if current_time - req_time < window]
    
    # Check if the client has exceeded the rate limit
    if len(client["requests"]) >= max_requests:
        # Block the client for 1 minute
        client["blocked_until"] = current_time + 60
        return False, 60
    
    # Add current request timestamp
    client["requests"].append(current_time)
    return True, 0

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint for chat interactions"""
    # Get client IP for rate limiting
    client_ip = request.remote_addr
    
    # Check rate limit
    allowed, wait_time = check_rate_limit(client_ip)
    if not allowed:
        return jsonify({
            "error": f"Rate limit exceeded. Please try again in {int(wait_time)} seconds.",
            "success": False
        }), 429
    
    data = request.json
    if not data:
        return jsonify({"error": "No data provided", "success": False}), 400
    
    message = data.get('message')
    session_id = data.get('session_id', 'default')
    
    if not message:
        return jsonify({"error": "No message provided", "success": False}), 400
    
    # Get or create chat session
    if session_id not in chat_sessions:
        chat_sessions[session_id] = GeminiChat()
        
        # Create a new chat record in the database
        db_chat = Chat(session_id=session_id)
        db.session.add(db_chat)
        db.session.commit()
    
    chat_session = chat_sessions[session_id]
    
    try:
        # Store user message in database
        db_chat = Chat.query.filter_by(session_id=session_id).first()
        if db_chat:
            user_message = Message(chat_id=db_chat.id, role="user", content=message)
            db.session.add(user_message)
            db.session.commit()
        
        # Get response from Gemini model - using the synchronous method
        response = chat_session.get_response(message)
        
        # If the response contains an error, log it
        if not response.get('success', False):
            logger.error(f"Error from Gemini: {response.get('error')}")
            return jsonify(response), 500
        
        # Store assistant response in database
        message_id = None
        if db_chat and response.get('response'):
            assistant_message = Message(
                chat_id=db_chat.id, 
                role="assistant", 
                content=response.get('response')
            )
            db.session.add(assistant_message)
            db.session.commit()
            message_id = assistant_message.id
        
        # Add message_id to the response for feedback functionality
        response['message_id'] = message_id
        
        # Return successful response
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e),
            "success": False
        }), 500

@chat_bp.route('/api/reset', methods=['POST'])
def reset_chat():
    """Endpoint to reset chat history"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided", "success": False}), 400
    
    session_id = data.get('session_id', 'default')
    
    # Reset chat history in memory
    if session_id in chat_sessions:
        chat_sessions[session_id].clear_history()
    
    # Create a new chat session in the database
    try:
        # Find the existing chat
        db_chat = Chat.query.filter_by(session_id=session_id).first()
        
        if db_chat:
            # Create a new chat to "reset" the history
            new_db_chat = Chat(session_id=session_id)
            db.session.add(new_db_chat)
            db.session.commit()
    except Exception as e:
        logger.error(f"Error resetting chat in database: {e}")
        # Continue with the reset even if database operations fail
    
    return jsonify({"message": "Chat history cleared", "success": True})

@chat_bp.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Endpoint to submit feedback on a message"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided", "success": False}), 400
    
    # Extract feedback data from request
    message_id = data.get('message_id')
    rating = data.get('rating')
    comment = data.get('comment', '')
    
    # Validate required fields
    if not message_id:
        return jsonify({"error": "Message ID is required", "success": False}), 400
    
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be an integer between 1 and 5", "success": False}), 400
    
    try:
        # Check if message exists
        message = Message.query.get(message_id)
        if not message:
            return jsonify({"error": f"Message with ID {message_id} not found", "success": False}), 404
        
        # Check if feedback already exists for this message
        existing_feedback = Feedback.query.filter_by(message_id=message_id).first()
        if existing_feedback:
            # Update existing feedback
            existing_feedback.rating = rating
            existing_feedback.comment = comment
            db.session.commit()
            
            return jsonify({
                "message": "Feedback updated successfully",
                "success": True,
                "feedback_id": existing_feedback.id
            })
        
        # Create new feedback
        feedback = Feedback(message_id=message_id, rating=rating, comment=comment)
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            "message": "Feedback submitted successfully",
            "success": True,
            "feedback_id": feedback.id
        })
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({
            "error": "Failed to submit feedback",
            "details": str(e),
            "success": False
        }), 500
        
@chat_bp.route('/api/history', methods=['GET'])
def get_chat_history():
    """Endpoint to get chat history for a session"""
    session_id = request.args.get('session_id', 'default')
    
    try:
        # Find the most recent chat for this session
        chat = Chat.query.filter_by(session_id=session_id).order_by(Chat.created_at.desc()).first()
        
        if not chat:
            return jsonify({
                "messages": [],
                "success": True
            })
        
        # Get messages for this chat
        messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.timestamp.asc()).all()
        
        # Format messages for response
        formatted_messages = []
        for msg in messages:
            message_data = {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            
            # Include feedback if available
            if hasattr(msg, 'feedback') and msg.feedback:
                message_data["feedback"] = {
                    "rating": msg.feedback.rating,
                    "comment": msg.feedback.comment
                }
            
            formatted_messages.append(message_data)
        
        return jsonify({
            "messages": formatted_messages,
            "success": True
        })
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({
            "error": "Failed to retrieve chat history",
            "details": str(e),
            "success": False
        }), 500
