document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const chatContainer = document.getElementById('chatContainer');
    const messageForm = document.getElementById('messageForm');
    const userMessageInput = document.getElementById('userMessage');
    const resetBtn = document.getElementById('resetBtn');
    const errorAlert = document.getElementById('errorAlert');
    const suggestionBtns = document.querySelectorAll('.suggestion-btn');
    
    // Generate a unique session ID for this chat session
    const sessionId = 'session_' + Date.now();
    
    // Load chat history when page loads
    loadChatHistory();
    
    // Function to display messages
    function displayMessage(content, isUser, messageId = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'user-message' : 'assistant-message';
        
        // If message has an ID, store it for feedback functionality
        if (messageId) {
            messageDiv.dataset.messageId = messageId;
        }
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = isUser ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Process markdown-like formatting in the assistant's response
        if (!isUser) {
            // Handle code blocks
            content = content.replace(/```([\s\S]*?)```/g, function(match, p1) {
                return `<pre><code>${p1}</code></pre>`;
            });
            
            // Handle inline code
            content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
            
            // Handle bold text
            content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            
            // Handle italic text
            content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
            
            // Handle bullet points
            content = content.replace(/^- (.*?)$/gm, '<li>$1</li>');
            content = content.replace(/<li>(.*?)<\/li>/g, function(match) {
                return '<ul>' + match + '</ul>';
            }).replace(/<\/ul><ul>/g, '');
            
            // Handle numbered lists
            content = content.replace(/^\d+\. (.*?)$/gm, '<li>$1</li>');
            content = content.replace(/<li>(.*?)<\/li>/g, function(match) {
                if (!match.includes('<ul>')) {
                    return '<ol>' + match + '</ol>';
                }
                return match;
            }).replace(/<\/ol><ol>/g, '');
        }
        
        // Create paragraphs for each line break
        const paragraphs = content.split('\n\n');
        paragraphs.forEach((paragraph, index) => {
            if (paragraph.trim()) {
                const p = document.createElement('p');
                p.innerHTML = paragraph;
                contentDiv.appendChild(p);
            }
        });
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        chatContainer.appendChild(messageDiv);
        
        // Scroll to the bottom of the chat container
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return messageDiv;
    }
    
    // Function to show typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typingIndicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'dot';
            typingDiv.appendChild(dot);
        }
        
        chatContainer.appendChild(typingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Function to remove typing indicator
    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Function to show error message
    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.classList.remove('d-none');
        setTimeout(() => {
            errorAlert.classList.add('d-none');
        }, 5000);
    }
    
    // Function to send a message to the API
    async function sendMessage(message) {
        try {
            // Display user message
            displayMessage(message, true);
            
            // Show typing indicator
            showTypingIndicator();
            
            // Clear input field
            userMessageInput.value = '';
            
            // Send request to API
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            removeTypingIndicator();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to get a response from the server');
            }
            
            if (!data.success) {
                throw new Error(data.error || 'An error occurred');
            }
            
            // Display assistant response with message ID for feedback
            const messageElement = displayMessage(data.response, false, data.message_id);
            
            // Add feedback functionality to the message
            addFeedbackComponent(messageElement, data.message_id);
            
        } catch (error) {
            // Remove typing indicator
            removeTypingIndicator();
            
            // Show error message
            showError(error.message);
            console.error('Error:', error);
        }
    }
    
    // Event listener for form submission
    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = userMessageInput.value.trim();
        if (message) {
            sendMessage(message);
        }
    });
    
    // Event listener for reset button
    resetBtn.addEventListener('click', async function() {
        try {
            const response = await fetch('/api/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: sessionId
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to reset chat history');
            }
            
            // Clear the chat container except for the welcome message
            while (chatContainer.lastChild && !chatContainer.lastChild.classList.contains('welcome-message')) {
                chatContainer.removeChild(chatContainer.lastChild);
            }
            
            // Show success message
            const resetMessage = 'Chat history has been reset. You can start a new conversation.';
            displayMessage(resetMessage, false);
            
        } catch (error) {
            showError(error.message);
            console.error('Error:', error);
        }
    });
    
    // Event listeners for suggestion buttons
    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const message = this.textContent.trim();
            userMessageInput.value = message;
            sendMessage(message);
        });
    });
    
    // Focus on input field when page loads
    userMessageInput.focus();
    
    // Function to load chat history from the server
    async function loadChatHistory() {
        try {
            const response = await fetch(`/api/history?session_id=${sessionId}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to load chat history');
            }
            
            if (!data.success) {
                throw new Error(data.error || 'An error occurred loading history');
            }
            
            // Clear welcome message if we have history
            if (data.messages && data.messages.length > 0) {
                // Remove welcome message
                const welcomeMessage = document.querySelector('.welcome-message');
                if (welcomeMessage) {
                    welcomeMessage.remove();
                }
                
                // Display each message in the history
                data.messages.forEach(msg => {
                    const isUser = msg.role === 'user';
                    const messageElement = displayMessage(msg.content, isUser, isUser ? null : msg.id);
                    
                    // Add feedback component to assistant messages
                    if (!isUser) {
                        addFeedbackComponent(messageElement, msg.id, msg.feedback);
                    }
                });
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
            // Don't show error to user to avoid disrupting the initial experience
            // Just continue with an empty chat
        }
    }
    
    // Function to add feedback component to assistant messages
    function addFeedbackComponent(messageElement, messageId, existingFeedback = null) {
        if (!messageElement || !messageId) return;
        
        // Find the message content div
        const contentDiv = messageElement.querySelector('.message-content');
        if (!contentDiv) return;
        
        // Create feedback component
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'message-feedback';
        
        // If message already has feedback, show it differently
        if (existingFeedback) {
            feedbackDiv.innerHTML = `
                <div class="feedback-success">
                    <i class="fas fa-check-circle"></i> Thanks for your feedback!
                    (Rated ${existingFeedback.rating}/5)
                </div>
            `;
            contentDiv.appendChild(feedbackDiv);
            return;
        }
        
        // Create the basic feedback structure
        feedbackDiv.innerHTML = `
            <span class="feedback-prompt">Was this response helpful?</span>
            <div class="rating-stars">
                <i class="far fa-star" data-rating="1"></i>
                <i class="far fa-star" data-rating="2"></i>
                <i class="far fa-star" data-rating="3"></i>
                <i class="far fa-star" data-rating="4"></i>
                <i class="far fa-star" data-rating="5"></i>
            </div>
            <div class="feedback-comment d-none">
                <textarea placeholder="Optional: Tell us more about your feedback" class="form-control mt-2"></textarea>
                <button class="btn btn-sm btn-primary mt-2 submit-feedback-btn">Submit</button>
            </div>
        `;
        
        contentDiv.appendChild(feedbackDiv);
        
        // Add event listeners for star ratings
        const stars = feedbackDiv.querySelectorAll('.rating-stars i');
        let selectedRating = 0;
        
        stars.forEach(star => {
            star.addEventListener('click', function() {
                // Get the selected rating
                selectedRating = parseInt(this.dataset.rating);
                
                // Update the UI to reflect the selected rating
                stars.forEach(s => {
                    const rating = parseInt(s.dataset.rating);
                    // Use filled stars for selected rating and below
                    if (rating <= selectedRating) {
                        s.classList.remove('far');
                        s.classList.add('fas');
                    } else {
                        s.classList.remove('fas');
                        s.classList.add('far');
                    }
                });
                
                // Show the comment box for feedback, especially if rating is low
                feedbackDiv.querySelector('.feedback-comment').classList.remove('d-none');
            });
        });
        
        // Add event listener for the submit button
        const submitBtn = feedbackDiv.querySelector('.submit-feedback-btn');
        submitBtn.addEventListener('click', async function() {
            if (!selectedRating) {
                // If no rating selected, highlight the stars as a reminder
                feedbackDiv.querySelector('.rating-stars').classList.add('animate__animated', 'animate__pulse');
                setTimeout(() => {
                    feedbackDiv.querySelector('.rating-stars').classList.remove('animate__animated', 'animate__pulse');
                }, 1000);
                return;
            }
            
            // Get the comment if any
            const comment = feedbackDiv.querySelector('textarea').value;
            
            try {
                // Submit feedback to the server
                const response = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message_id: messageId,
                        rating: selectedRating,
                        comment: comment
                    })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to submit feedback');
                }
                
                if (!data.success) {
                    throw new Error(data.error || 'An error occurred');
                }
                
                // Replace feedback form with thank you message
                feedbackDiv.innerHTML = `
                    <div class="feedback-success">
                        <i class="fas fa-check-circle"></i> Thanks for your feedback!
                    </div>
                `;
                
            } catch (error) {
                // Show error message
                console.error('Error submitting feedback:', error);
                feedbackDiv.innerHTML += `
                    <div class="alert alert-danger mt-2">
                        Failed to submit feedback. Please try again later.
                    </div>
                `;
            }
        });
    }
});
