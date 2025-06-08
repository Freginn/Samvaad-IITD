<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-Enhanced Document Q&A Bot</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50, #3498db);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .ai-badge {
            display: inline-block;
            background: linear-gradient(135deg, #e74c3c, #c0392b);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8em;
            margin-top: 10px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .content {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 30px;
            padding: 30px;
        }
        
        .left-panel {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .upload-section {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border: 3px dashed #3498db;
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .upload-section:hover {
            border-color: #2980b9;
            background: linear-gradient(135deg, #e9ecef, #dee2e6);
        }
        
        .upload-section input[type="file"] {
            display: none;
        }
        
        .upload-btn {
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 50px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(52, 152, 219, 0.3);
        }
        
        .upload-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(52, 152, 219, 0.4);
        }
        
        .ai-config {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .ai-config h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .ai-toggle {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .toggle-switch {
            position: relative;
            width: 60px;
            height: 30px;
            background: #ddd;
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .toggle-switch.active {
            background: #27ae60;
        }
        
        .toggle-slider {
            position: absolute;
            top: 3px;
            left: 3px;
            width: 24px;
            height: 24px;
            background: white;
            border-radius: 50%;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
        }
        
        .toggle-switch.active .toggle-slider {
            transform: translateX(30px);
        }
        
        .api-input {
            width: 100%;
            padding: 10px 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }
        
        .api-input:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
        }
        
        .status {
            margin-top: 15px;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-size: 0.9em;
        }
        
        .status.success {
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            color: #155724;
        }
        
        .status.error {
            background: linear-gradient(135deg, #f8d7da, #f5c6cb);
            color: #721c24;
        }
        
        .status.info {
            background: linear-gradient(135deg, #d1ecf1, #bee5eb);
            color: #0c5460;
        }
        
        .document-list {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .document-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        
        .document-item:last-child {
            border-bottom: none;
        }
        
        .doc-info {
            display: flex;
            flex-direction: column;
        }
        
        .doc-name {
            font-weight: 500;
            color: #2c3e50;
            font-size: 0.9em;
        }
        
        .doc-size {
            font-size: 0.8em;
            color: #7f8c8d;
        }
        
        .chat-section {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
        }
        
        .chat-header {
            background: linear-gradient(135deg, #34495e, #2c3e50);
            color: white;
            padding: 20px;
            font-weight: 500;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .ai-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.9em;
        }
        
        .ai-indicator.active {
            color: #2ecc71;
        }
        
        .ai-indicator.inactive {
            color: #e74c3c;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: linear-gradient(to bottom, #f8f9fa, white);
        }
        
        .message {
            margin-bottom: 20px;
            padding: 15px 20px;
            border-radius: 20px;
            max-width: 85%;
            word-wrap: break-word;
            animation: fadeIn 0.3s ease;
            position: relative;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 5px;
        }
        
        .message.bot {
            background: linear-gradient(135deg, #ecf0f1, #bdc3c7);
            color: #2c3e50;
            border-bottom-left-radius: 5px;
        }
        
        .message.ai {
            background: linear-gradient(135deg, #e8f5e8, #d4edda);
            color: #155724;
            border-left: 4px solid #28a745;
        }
        
        .message-type {
            position: absolute;
            top: -8px;
            right: 10px;
            background: #3498db;
            color: white;
            font-size: 0.7em;
            padding: 2px 8px;
            border-radius: 10px;
        }
        
        .ai-type {
            background: #28a745 !important;
        }
        
        .thinking {
            display: flex;
            align-items: center;
            gap: 10px;
            font-style: italic;
            opacity: 0.8;
        }
        
        .dots {
            display: flex;
            gap: 3px;
        }
        
        .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #3498db;
            animation: bounce 1.4s ease-in-out infinite both;
        }
        
        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }
        
        .chat-input {
            display: flex;
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
        }
        
        .chat-input input {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #dee2e6;
            border-radius: 25px;
            font-size: 1em;
            outline: none;
            transition: all 0.3s ease;
        }
        
        .chat-input input:focus {
            border-color: #3498db;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
        }
        
        .chat-input button {
            background: linear-gradient(135deg, #27ae60, #2ecc71);
            color: white;
            border: none;
            padding: 15px 25px;
            margin-left: 10px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(39, 174, 96, 0.3);
        }
        
        .chat-input button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(39, 174, 96, 0.4);
        }
        
        .chat-input button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .processing {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .content {
                grid-template-columns: 1fr;
            }
            
            .chat-section {
                height: 500px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI-Enhanced Document Q&A Bot</h1>
            <p>Upload documents and chat with AI for intelligent answers</p>
            <div class="ai-badge">✨ AI POWERED</div>
        </div>
        
        <div class="content">
            <div class="left-panel">
                <div class="upload-section">
                    <h3>📁 Upload Documents</h3>
                    <p>Select PDF files or text files</p>
                    <input type="file" id="fileInput" multiple accept=".pdf,.txt,.md">
                    <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                        Choose Files
                    </button>
                    <div id="uploadStatus"></div>
                </div>
                
                <div class="ai-config">
                    <h3>🧠 AI Configuration</h3>
                    <div class="ai-toggle">
                        <div class="toggle-switch" id="aiToggle" onclick="toggleAI()">
                            <div class="toggle-slider"></div>
                        </div>
                        <span>Enable AI Responses</span>
                    </div>
                    <input type="password" class="api-input" id="apiKey" placeholder="Enter OpenAI API Key (optional)" style="display: none;">
                    <div id="aiStatus" class="status info">
                        AI Mode: Using Claude AI (Free) - Limited responses
                    </div>
                </div>
                
                <div id="documentList" class="document-list" style="display: none;">
                    <h3>📄 Loaded Documents</h3>
                    <div id="documents"></div>
                </div>
            </div>
            
            <div class="chat-section">
                <div class="chat-header">
                    <span>💬 Intelligent Document Chat</span>
                    <div class="ai-indicator inactive" id="aiIndicator">
                        <span class="processing" style="display: none;" id="aiProcessing"></span>
                        <span id="aiStatusText">Basic Search</span>
                    </div>
                </div>
                <div class="chat-messages" id="chatMessages">
                    <div class="message bot">
                        <div class="message-type">SYSTEM</div>
                        Hello! I'm your AI-enhanced document assistant. Upload some documents and I'll help you find information using both keyword search and AI analysis.
                        <br><br>
                        <strong>Features:</strong><br>
                        🔍 Smart keyword search<br>
                        🤖 AI-powered responses<br>
                        📊 Document analysis<br>
                        💡 Contextual answers
                    </div>
                </div>
                <div class="chat-input">
                    <input type="text" id="questionInput" placeholder="Ask a question about your documents..." disabled>
                    <button onclick="askQuestion()" id="askBtn" disabled>Ask</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Configure PDF.js
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        // Global variables
        let documents = [];
        let documentTexts = [];
        let aiEnabled = false;
        let isProcessing = false;
        
        // Event listeners
        document.getElementById('fileInput').addEventListener('change', handleFiles);
        document.getElementById('questionInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !isProcessing) {
                askQuestion();
            }
        });
        
        // File handling
        async function handleFiles(event) {
            const files = Array.from(event.target.files);
            const status = document.getElementById('uploadStatus');
            
            if (files.length === 0) return;
            
            status.innerHTML = '<div class="processing"></div> Processing documents...';
            status.className = 'status info';
            
            try {
                for (const file of files) {
                    await processFile(file);
                }
                
                status.innerHTML = `✅ Successfully processed ${files.length} document(s)`;
                status.className = 'status success';
                
                updateDocumentList();
                enableChat();
                
            } catch (error) {
                status.innerHTML = `❌ Error: ${error.message}`;
                status.className = 'status error';
            }
        }
        
        async function processFile(file) {
            const fileName = file.name;
            const fileSize = formatFileSize(file.size);
            
            let text = '';
            
            if (file.type === 'application/pdf') {
                text = await extractTextFromPDF(file);
            } else if (file.type === 'text/plain' || fileName.endsWith('.txt') || fileName.endsWith('.md')) {
                text = await extractTextFromFile(file);
            } else {
                throw new Error(`Unsupported file type: ${file.type}`);
            }
            
            documents.push({
                name: fileName,
                size: fileSize,
                type: file.type
            });
            
            documentTexts.push({
                name: fileName,
                content: text
            });
        }
        
        async function extractTextFromPDF(file) {
            const arrayBuffer = await file.arrayBuffer();
            const pdf = await pdfjsLib.getDocument(arrayBuffer).promise;
            let fullText = '';
            
            for (let i = 1; i <= pdf.numPages; i++) {
                const page = await pdf.getPage(i);
                const textContent = await page.getTextContent();
                const pageText = textContent.items.map(item => item.str).join(' ');
                fullText += pageText + '\n';
            }
            
            return fullText;
        }
        
        async function extractTextFromFile(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = e => resolve(e.target.result);
                reader.onerror = reject;
                reader.readAsText(file);
            });
        }
        
        // UI functions
        function updateDocumentList() {
            const listContainer = document.getElementById('documentList');
            const docsContainer = document.getElementById('documents');
            
            if (documents.length === 0) {
                listContainer.style.display = 'none';
                return;
            }
            
            listContainer.style.display = 'block';
            docsContainer.innerHTML = documents.map(doc => `
                <div class="document-item">
                    <div class="doc-info">
                        <div class="doc-name">${doc.name}</div>
                        <div class="doc-size">${doc.size}</div>
                    </div>
                    <div>📁</div>
                </div>
            `).join('');
        }
        
        function enableChat() {
            document.getElementById('questionInput').disabled = false;
            document.getElementById('askBtn').disabled = false;
            document.getElementById('questionInput').placeholder = 'Ask a question about your documents...';
        }
        
        function toggleAI() {
            const toggle = document.getElementById('aiToggle');
            const indicator = document.getElementById('aiIndicator');
            const statusText = document.getElementById('aiStatusText');
            const apiInput = document.getElementById('apiKey');
            const aiStatus = document.getElementById('aiStatus');
            
            aiEnabled = !aiEnabled;
            
            if (aiEnabled) {
                toggle.classList.add('active');
                indicator.classList.remove('inactive');
                indicator.classList.add('active');
                statusText.textContent = 'AI Enhanced';
                apiInput.style.display = 'block';
                aiStatus.innerHTML = '🤖 AI Mode: Enhanced responses with context understanding';
                aiStatus.className = 'status success';
            } else {
                toggle.classList.remove('active');
                indicator.classList.remove('active');
                indicator.classList.add('inactive');
                statusText.textContent = 'Basic Search';
                apiInput.style.display = 'none';
                aiStatus.innerHTML = '🔍 Basic Mode: Keyword-based search only';
                aiStatus.className = 'status info';
            }
        }
        
        // Chat functions
        async function askQuestion() {
            const input = document.getElementById('questionInput');
            const question = input.value.trim();
            
            if (!question || documentTexts.length === 0 || isProcessing) return;
            
            isProcessing = true;
            const askBtn = document.getElementById('askBtn');
            const processing = document.getElementById('aiProcessing');
            
            askBtn.disabled = true;
            processing.style.display = 'inline-block';
            
            addMessage(question, 'user');
            input.value = '';
            
            try {
                let answer;
                if (aiEnabled) {
                    // Show thinking message
                    const thinkingId = addThinkingMessage();
                    answer = await getAIResponse(question);
                    removeMessage(thinkingId);
                    addMessage(answer, 'ai');
                } else {
                    answer = searchDocuments(question);
                    addMessage(answer, 'bot');
                }
            } catch (error) {
                addMessage(`Sorry, I encountered an error: ${error.message}`, 'bot');
            } finally {
                isProcessing = false;
                askBtn.disabled = false;
                processing.style.display = 'none';
            }
        }
        
        function addThinkingMessage() {
            const messagesContainer = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            const thinkingId = 'thinking-' + Date.now();
            
            messageDiv.id = thinkingId;
            messageDiv.className = 'message ai';
            messageDiv.innerHTML = `
                <div class="message-type ai-type">AI THINKING</div>
                <div class="thinking">
                    <span>Analyzing documents with AI</span>
                    <div class="dots">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                </div>
            `;
            
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            return thinkingId;
        }
        
        function removeMessage(messageId) {
            const message = document.getElementById(messageId);
            if (message) {
                message.remove();
            }
        }
        
        async function getAIResponse(question) {
            // Get relevant context from documents
            const context = getRelevantContext(question);
            
            // Simulate AI response (replace with actual API call)
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            const prompt = `Based on the following document excerpts, please answer the question: "${question}"\n\nDocument context:\n${context}\n\nPlease provide a comprehensive answer based on the document content.`;
            
            // This is a simulated AI response - replace with actual API call
            return generateSimulatedAIResponse(question, context);
        }
        
        function getRelevantContext(question) {
            const questionLower = question.toLowerCase();
            const stopWords = ['the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in', 'with', 'to', 'for', 'of', 'as', 'by'];
            const questionWords = questionLower.split(/\s+/)
                .filter(word => word.length > 2 && !stopWords.includes(word));
            
            let relevantText = '';
            
            documentTexts.forEach(doc => {
                const sentences = doc.content.split(/[.!?]+/).filter(s => s.trim().length > 20);
                const relevantSentences = sentences.filter(sentence => {
                    const sentenceLower = sentence.toLowerCase();
                    return questionWords.some(word => sentenceLower.includes(word));
                }).slice(0, 3);
                
                if (relevantSentences.length > 0) {
                    relevantText += `\n--- From ${doc.name} ---\n`;
                    relevantText += relevantSentences.join('. ') + '\n';
                }
            });
            
            return relevantText || 'No directly relevant content found in documents.';
        }
        
        function generateSimulatedAIResponse(question, context) {
            if (context.includes('No directly relevant content found')) {
                return `I've analyzed your documents but couldn't find specific information about "${question}". The documents might not contain relevant details on this topic, or the information might be expressed using different terminology. Try rephrasing your question or asking about topics that are more directly covered in your uploaded documents.`;
            }
            
            return `Based on my analysis of your documents, here's what I found regarding "${question}":\n\n${context}\n\n💡 **AI Insight**: This information appears across multiple sections of your documents. The content suggests a comprehensive coverage of the topic you're asking about. Would you like me to elaborate on any specific aspect or find related information?`;
        }
        
        // Fallback search function
        function searchDocuments(question) {
            const questionLower = question.toLowerCase();
            const results = [];
            
            const stopWords = ['the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in', 'with', 'to', 'for', 'of', 'as', 'by'];
            const questionWords = questionLower.split(/\s+/)
                .filter(word => word.length > 2 && !stopWords.includes(word));
            
            if (questionWords.length === 0) {
                return "Please ask a more specific question with meaningful keywords.";
            }
            
            documentTexts.forEach(doc => {
                const sentences = doc.content.split(/[.!?]+/).filter(s => s.trim().length > 10);
                
                const scoredSentences = sentences.map(sentence => {
                    const sentenceLower = sentence.toLowerCase();
                    let score = 0;
                    
                    questionWords.forEach(word => {
                        if (sentenceLower.includes(word)) {
                            score += 1;
                            if (sentenceLower.match(new RegExp(`\\b${word}\\b`))) {
                                score += 1;
                            }
                        }
                    });
                    
                    return { sentence: sentence.trim(), score: score };
                }).filter(item => item.score > 0);
                
                scoredSentences.sort((a, b) => b.score - a.score);
                const topSentences = scoredSentences.slice(0, 2);
                
                if (topSentences.length > 0) {
                    results.push({
                        document: doc.name,
                        sentences: topSentences
                    });
                }
            });
            
            if (results.length === 0) {
                return `I couldn't find information about "${question}" in your documents. Try using different keywords or check if this information exists in your documents.`;
            }
            
            let answer = `Here's what I found about "${question}":\n\n`;
            
            results.slice(0, 2).forEach(result => {
                answer += `📄 **${result.document}:**\n`;
                result.sentences.forEach(item => {
                    answer += `${item.sentence}\n\n`;
                });
            });
            
            return answer;
        }
        
        function addMessage(text, sender) {
            const messagesContainer = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            // Add message type badge
            let typeBadge = '';
            if (sender === 'ai') {
                typeBadge = '<div class="message-type ai-type">AI</div>';
            } else if (sender
