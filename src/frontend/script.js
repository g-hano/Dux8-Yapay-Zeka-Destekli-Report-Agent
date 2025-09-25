// DOM Elements
const tabs = document.querySelectorAll('.nav-tab');
const tabContents = document.querySelectorAll('.tab-content');
const notification = document.getElementById('notification');

const API_BASE_URL = 'http://localhost:8000/api';

// Tab Navigation
tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const tabId = tab.getAttribute('data-tab');
        
        // Deactivate all tabs and contents
        tabs.forEach(t => t.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        
        // Activate selected tab and content
        tab.classList.add('active');
        document.getElementById(tabId).classList.add('active');
    });
});

// Show notification
function showNotification(message, type = 'success') {
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Show loading spinner
function showLoading(container) {
    container.innerHTML = '<div class="loading"><div class="spinner"></div> Processing...</div>';
}

// RAG Tab Functionality
const ragUploadArea = document.getElementById('rag-upload-area');
const ragFileInput = document.getElementById('rag-file-input');
const ragFileInfo = document.getElementById('rag-file-info');
const ragFileName = document.getElementById('rag-file-name');
const ragFileId = document.getElementById('rag-file-id');
const ragChatContainer = document.getElementById('rag-chat-container');
const ragMessages = document.getElementById('rag-messages');
const ragInput = document.getElementById('rag-input');
const ragSendBtn = document.getElementById('rag-send-btn');
const ragDebug = document.getElementById('rag-debug');
const ragDebugContent = document.getElementById('rag-debug-content');
const ragToggleDebug = document.getElementById('rag-toggle-debug');

let ragFileIdValue = null;

ragUploadArea.addEventListener('click', () => ragFileInput.click());

ragUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    ragUploadArea.classList.add('active');
});

ragUploadArea.addEventListener('dragleave', () => {
    ragUploadArea.classList.remove('active');
});

ragUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    ragUploadArea.classList.remove('active');
    
    if (e.dataTransfer.files.length) {
        handleRagFileUpload(e.dataTransfer.files[0]);
    }
});

ragFileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleRagFileUpload(e.target.files[0]);
    }
});

ragToggleDebug.addEventListener('click', () => {
    if (ragDebug.style.display === 'none') {
        ragDebug.style.display = 'block';
    } else {
        ragDebug.style.display = 'none';
    }
});

async function handleRagFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Determine the correct endpoint based on file type
    // bu saçma oldu
    const isPdf = true //file.name.toLowerCase().endsWith('.pdf');
    const endpoint = isPdf ? `${API_BASE_URL}/llama-parse/` : `${API_BASE_URL}/parse/`;
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }
        
        const result = await response.json();
        ragFileIdValue = result.file_id;
        
        ragFileName.textContent = `File: ${file.name}`;
        ragFileId.textContent = `File ID: ${result.file_id}`;
        ragFileInfo.style.display = 'block';
        ragChatContainer.style.display = 'block';
        
        // Add a welcome message
        const welcomeMessage = document.createElement('div');
        welcomeMessage.className = 'chat-message bot-message';
        welcomeMessage.textContent = `Document "${file.name}" has been uploaded and processed. You can now ask questions about its content.`;
        ragMessages.appendChild(welcomeMessage);
        
        showNotification('Document uploaded successfully!');
    } catch (error) {
        showNotification('Error uploading document: ' + error.message, 'error');
        console.error('Upload error:', error);
    }
}


ragSendBtn.addEventListener('click', sendRagMessage);
ragInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendRagMessage();
});

async function sendRagMessage() {
    const query = ragInput.value.trim();
    if (!query || !ragFileIdValue) return;
    
    // Add user message to chat
    const userMessage = document.createElement('div');
    userMessage.className = 'chat-message user-message';
    userMessage.textContent = query;
    ragMessages.appendChild(userMessage);
    
    ragInput.value = '';
    
    // Add loading message
    const botMessage = document.createElement('div');
    botMessage.className = 'chat-message bot-message';
    botMessage.innerHTML = '<div class="spinner"></div> Thinking...';
    ragMessages.appendChild(botMessage);
    
    // Scroll to bottom
    ragMessages.scrollTop = ragMessages.scrollHeight;
    
    try {
        console.log('Sending query:', query);
        console.log('Using file_id:', ragFileIdValue);
        
        const response = await fetch(`${API_BASE_URL}/query/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: ragFileIdValue,
                query: query
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Query failed');
        }
        
        const result = await response.json();
        
        console.log('Query response:', result);
        
        ragDebugContent.innerHTML = `
            <p><strong>Query:</strong> ${result.query}</p>
            <p><strong>Response:</strong> ${JSON.stringify(result, null, 2)}</p>
        `;
        
        botMessage.innerHTML = result.answer;

        // Add sources if available
        if (result.sources && result.sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.style.marginTop = '10px';
            sourcesDiv.style.fontSize = '12px';
            sourcesDiv.style.color = '#666';
            sourcesDiv.innerHTML = '<strong>Sources:</strong>';
            
            const sourcesList = document.createElement('ul');
            sourcesList.style.marginTop = '5px';
            sourcesList.style.paddingLeft = '20px';
            
            result.sources.forEach(source => {
                const sourceItem = document.createElement('li');
                sourceItem.textContent = source.text;
                sourcesList.appendChild(sourceItem);
            });
            
            sourcesDiv.appendChild(sourcesList);
            botMessage.appendChild(sourcesDiv);
        }
    } catch (error) {
        botMessage.innerHTML = `Error: ${error.message}`;
        console.error('Query error:', error);
    }
    
    // Scroll to bottom
    ragMessages.scrollTop = ragMessages.scrollHeight;
}

// Summarization Tab Functionality
const summaryUploadArea = document.getElementById('summary-upload-area');
const summaryFileInput = document.getElementById('summary-file-input');
const summaryMaxLength = document.getElementById('summary-max-length');
const summaryFocus = document.getElementById('summary-focus');
const generateSummaryBtn = document.getElementById('generate-summary-btn');
const summaryResult = document.getElementById('summary-result');
const summaryError = document.getElementById('summary-error');
const summaryContent = document.getElementById('summary-content');
const summaryErrorMessage = document.getElementById('summary-error-message');
const summaryErrorDetails = document.getElementById('summary-error-details');
const originalWords = document.getElementById('original-words');
const summaryWords = document.getElementById('summary-words');
const compressionRatio = document.getElementById('compression-ratio');

let summaryFileId = null;

summaryUploadArea.addEventListener('click', () => summaryFileInput.click());

summaryUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    summaryUploadArea.classList.add('active');
});

summaryUploadArea.addEventListener('dragleave', () => {
    summaryUploadArea.classList.remove('active');
});

summaryUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    summaryUploadArea.classList.remove('active');
    
    if (e.dataTransfer.files.length) {
        handleSummaryFileUpload(e.dataTransfer.files[0]);
    }
});

summaryFileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleSummaryFileUpload(e.target.files[0]);
    }
});

generateSummaryBtn.addEventListener('click', generateSummary);

async function handleSummaryFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Determine the correct endpoint based on file type
    const isPdf = file.name.toLowerCase().endsWith('.pdf');
    const endpoint = isPdf ? `${API_BASE_URL}/llama-parse/` : `${API_BASE_URL}/parse/`;
    
    // Reset UI
    summaryResult.style.display = 'none';
    summaryError.style.display = 'none';
    generateSummaryBtn.style.display = 'block';
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }
        
        const result = await response.json();
        summaryFileId = result.file_id;
        
        showNotification('Document uploaded successfully! Configure your summary options and click Generate.');
    } catch (error) {
        showNotification('Error uploading document: ' + error.message, 'error');
        console.error('Upload error:', error);
    }
}


async function generateSummary() {
    if (!summaryFileId) return;
    
    // Reset UI
    summaryResult.style.display = 'none';
    summaryError.style.display = 'none';
    showLoading(summaryContent);
    summaryResult.style.display = 'block';
    
    try {
        const maxLength = parseInt(summaryMaxLength.value) || 500;
        const focus = summaryFocus.value.trim();
        
        const requestBody = {
            file_id: summaryFileId,
            max_length: maxLength
        };
        
        // Add focus if provided
        if (focus) {
            requestBody.focus = focus;
        }
        
        console.log('Sending summary request:', requestBody);
        
        const response = await fetch(`${API_BASE_URL}/summary/summarize/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Summarization failed');
        }
        
        const summaryResultData = await response.json();
        
        console.log('Summary response:', summaryResultData);
        
        // Calculate statistics (approximate)
        const summaryWordCount = summaryResultData.summary.split(' ').length;
        const originalWordCount = Math.round(summaryWordCount * 2.5); // Estimate based on typical compression
        const compression = Math.round((1 - (summaryWordCount / originalWordCount)) * 100);
        
        // Display summary
        summaryContent.innerHTML = `<p>${summaryResultData.summary}</p>`;
        originalWords.textContent = originalWordCount;
        summaryWords.textContent = summaryWordCount;
        compressionRatio.textContent = `${compression}%`;
        
        showNotification('Summary generated successfully!');
    } catch (error) {
        // Display error
        summaryResult.style.display = 'none';
        summaryError.style.display = 'block';
        summaryErrorMessage.textContent = error.message;
        summaryErrorDetails.textContent = JSON.stringify(error, null, 2);
        
        showNotification('Error generating summary: ' + error.message, 'error');
        console.error('Summary error:', error);
    }
}

// Report Creation Tab Functionality
const reportUploadArea = document.getElementById('report-upload-area');
const reportFileInput = document.getElementById('report-file-input');
const reportResult = document.getElementById('report-result');
const reportContent = document.getElementById('report-content');

reportUploadArea.addEventListener('click', () => reportFileInput.click());

reportUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    reportUploadArea.classList.add('active');
});

reportUploadArea.addEventListener('dragleave', () => {
    reportUploadArea.classList.remove('active');
});

reportUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    reportUploadArea.classList.remove('active');
    
    if (e.dataTransfer.files.length) {
        handleReportFileUpload(e.dataTransfer.files[0]);
    }
});

reportFileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleReportFileUpload(e.target.files[0]);
    }
});

async function handleReportFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Determine the correct endpoint based on file type
    const isPdf = file.name.toLowerCase().endsWith('.pdf');
    const endpoint = isPdf ? `${API_BASE_URL}/llama-parse/` : `${API_BASE_URL}/parse/`;
    
    showLoading(reportContent);
    reportResult.style.display = 'block';
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }
        
        const parseResult = await response.json();
        
        // Generate report content
        if (isPdf) {
            // For PDF files
            reportContent.innerHTML = `
                <h4>Report: ${file.name}</h4>
                <p><strong>Character Count:</strong> ${parseResult.char_count}</p>
                <p><strong>Word Count:</strong> ${parseResult.word_count}</p>
                <div style="margin-top: 20px;">
                    <h4>Document Content</h4>
                    <div style="max-height: 300px; overflow-y: auto; padding: 10px; background-color: #f9f9f9; border-radius: 4px;">
                        ${parseResult.markdown_content.replace(/\n/g, '<br>')}
                    </div>
                </div>
            `;
        } else {
            // For structured data files
            reportContent.innerHTML = `
                <h4>Report: ${file.name}</h4>
                <p><strong>Rows:</strong> ${parseResult.summary.rows}</p>
                <p><strong>Columns:</strong> ${parseResult.summary.columns}</p>
                <div style="margin-top: 20px;">
                    <h4>Data Summary</h4>
                    <div style="max-height: 300px; overflow-y: auto; padding: 10px; background-color: #f9f9f9; border-radius: 4px;">
                        <pre>${JSON.stringify(parseResult.summary, null, 2)}</pre>
                    </div>
                </div>
            `;
        }
        
        showNotification('Report created successfully!');
    } catch (error) {
        reportContent.innerHTML = `<p>Error: ${error.message}</p>`;
        showNotification('Error creating report: ' + error.message, 'error');
        console.error('Report error:', error);
    }
}


// Trends & KPIs Tab Functionality
const trendUploadArea = document.getElementById('trend-upload-area');
const trendFileInput = document.getElementById('trend-file-input');
const trendResult = document.getElementById('trend-result');
const kpiContainer = document.getElementById('kpi-container');
const trendContainer = document.getElementById('trend-container');

trendUploadArea.addEventListener('click', () => trendFileInput.click());

trendUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    trendUploadArea.classList.add('active');
});

trendUploadArea.addEventListener('dragleave', () => {
    trendUploadArea.classList.remove('active');
});

trendUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    trendUploadArea.classList.remove('active');
    
    if (e.dataTransfer.files.length) {
        handleTrendFileUpload(e.dataTransfer.files[0]);
    }
});

trendFileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleTrendFileUpload(e.target.files[0]);
    }
});

async function handleTrendFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    showLoading(kpiContainer);
    trendResult.style.display = 'block';
    trendContainer.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/data/process-data/`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Processing failed');
        }
        
        const result = await response.json();
        
        console.log('Data processing result:', result);
        
        // Display KPIs
        kpiContainer.innerHTML = '';
        if (result.kpis && Object.keys(result.kpis).length > 0) {
            for (const [key, value] of Object.entries(result.kpis)) {
                const kpiCard = document.createElement('div');
                kpiCard.className = 'kpi-card';
                
                // Format the value as a JSON string for display
                const valueStr = typeof value === 'object' ? JSON.stringify(value, null, 2) : value;
                
                kpiCard.innerHTML = `
                    <i class="fas fa-chart-pie"></i>
                    <div>
                        <h3>${key}</h3>
                        <pre>${valueStr}</pre>
                    </div>
                `;
                kpiContainer.appendChild(kpiCard);
            }
        } else {
            kpiContainer.innerHTML = '<p>No KPIs found in the data.</p>';
        }
        
        // Display Trends
        if (result.trends && result.trends.length > 0) {
            result.trends.forEach(trend => {
                const trendItem = document.createElement('div');
                trendItem.className = 'trend-item';
                
                const directionClass = trend.direction === 'up' ? 'trend-up' : 'trend-down';
                const directionIcon = trend.direction === 'up' ? 'fa-arrow-up' : 'fa-arrow-down';
                
                trendItem.innerHTML = `
                    <h4>${trend.name}</h4>
                    <p>${trend.description}</p>
                    <p><span class="trend-value">${trend.value}</span> 
                    <span class="trend-direction ${directionClass}"><i class="fas ${directionIcon}"></i> ${trend.direction}</span></p>
                `;
                
                trendContainer.appendChild(trendItem);
            });
        } else {
            trendContainer.innerHTML = '<p>No trends identified in the data.</p>';
        }
        
        
        showNotification('Trends and KPIs extracted successfully!');
    } catch (error) {
        kpiContainer.innerHTML = `<p>Error: ${error.message}</p>`;
        showNotification('Error processing data: ' + error.message, 'error');
        console.error('Trend/KPI error:', error);
    }
}

// Action Items Tab Functionality
const actionUploadArea = document.getElementById('action-upload-area');
const actionFileInput = document.getElementById('action-file-input');
const businessContext = document.getElementById('business-context');
const actionResult = document.getElementById('action-result');
const actionContainer = document.getElementById('action-container');
const priorityFilter = document.getElementById('priority-filter');
let actionItemsData = null;

actionUploadArea.addEventListener('click', () => actionFileInput.click());

actionUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    actionUploadArea.classList.add('active');
});

actionUploadArea.addEventListener('dragleave', () => {
    actionUploadArea.classList.remove('active');
});

actionUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    actionUploadArea.classList.remove('active');
    
    if (e.dataTransfer.files.length) {
        handleActionFileUpload(e.dataTransfer.files[0]);
    }
});

actionFileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleActionFileUpload(e.target.files[0]);
    }
});
priorityFilter.addEventListener('change', filterActionItems);

async function handleActionFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('business_context', businessContext.value);
    
    showLoading(actionContainer);
    actionResult.style.display = 'block';
    
    try {
        const response = await fetch(`${API_BASE_URL}/data/process-data/`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Processing failed');
        }
        
        const result = await response.json();
        actionItemsData = result.action_items;
        displayActionItems(actionItemsData);
        if (result.action_items && result.action_items.summary) {
            const summaryDiv = document.createElement('div');
            summaryDiv.className = 'result-container';
            summaryDiv.innerHTML = `<h3>Summary</h3><p>${result.action_items.summary}</p>`;
            actionContainer.appendChild(summaryDiv);
        }

        console.log('Action items result:', result);

if (result.action_items && result.action_items.key_insights && result.action_items.key_insights.length > 0) {
    const insightsDiv = document.createElement('div');
    insightsDiv.className = 'result-container';
    insightsDiv.innerHTML = '<h3>Key Insights</h3><ul>' + 
        result.action_items.key_insights.map(insight => `<li>${insight}</li>`).join('') + 
        '</ul>';
    actionContainer.appendChild(insightsDiv);
}

showNotification('Action items generated successfully!');
} catch (error) {
    actionContainer.innerHTML = `<p>Error: ${error.message}</p>`;
    showNotification('Error generating action items: ' + error.message, 'error');
    console.error('Action items error:', error);
}
}
function displayActionItems(actionItems) {
    actionContainer.innerHTML = '';
    
    if (!actionItems || !actionItems.action_items || actionItems.action_items.length === 0) {
        actionContainer.innerHTML = '<p>No action items found.</p>';
        return;
    }
    const itemsContainer = document.createElement('div');
    itemsContainer.id = 'action-items-container';

    actionItems.action_items.forEach(item => {
        const actionItem = document.createElement('div');
        actionItem.className = 'action-item';
        
        // Set priority class for styling
        const priorityClass = item.priority ? `priority-${item.priority}` : '';
        
        actionItem.innerHTML = `
            <div class="priority ${priorityClass}">${item.priority || 'medium'}</div>
            <h4>${item.title || 'Untitled Action'}</h4>
            <p><strong>Category:</strong> ${item.category || 'general'}</p>
            <p><strong>Description:</strong> ${item.description || 'No description available'}</p>
            <p><strong>Expected Impact:</strong> ${item.expected_impact || 'Not specified'}</p>
            <p><strong>Timeline:</strong> ${item.timeline || 'Not specified'}</p>
            <p><strong>Responsible:</strong> ${item.responsible || 'Not specified'}</p>
        `;
        
        itemsContainer.appendChild(actionItem);
    });
    actionContainer.appendChild(itemsContainer);
}

function filterActionItems() {
    if (!actionItemsData || !actionItemsData.action_items) {
        return;
    }
    
    const selectedPriority = priorityFilter.value;
    
    if (selectedPriority === 'all') {
        // Show all action items
        displayActionItems(actionItemsData);
    } else {
        // Filter action items by priority
        const filteredItems = {
            ...actionItemsData,
            action_items: actionItemsData.action_items.filter(item => 
                item.priority && item.priority.toLowerCase() === selectedPriority.toLowerCase()
            )
        };
        
        displayActionItems(filteredItems);
    }
}





// Visualization Tab Functionality
const visualizationUploadArea = document.getElementById('visualization-upload-area');
const visualizationFileInput = document.getElementById('visualization-file-input');
const chartType = document.getElementById('chart-type');
const xColumn = document.getElementById('x-column');
const yColumn = document.getElementById('y-column');
const generateVisualizationBtn = document.getElementById('generate-visualization-btn');
const visualizationResult = document.getElementById('visualization-result');
const visualizationImage = document.getElementById('visualization-image');

let visualizationFile = null;

visualizationUploadArea.addEventListener('click', () => visualizationFileInput.click());

visualizationUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    visualizationUploadArea.classList.add('active');
});

visualizationUploadArea.addEventListener('dragleave', () => {
    visualizationUploadArea.classList.remove('active');
});

visualizationUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    visualizationUploadArea.classList.remove('active');
    
    if (e.dataTransfer.files.length) {
        handleVisualizationFileUpload(e.dataTransfer.files[0]);
    }
});

visualizationFileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleVisualizationFileUpload(e.target.files[0]);
    }
});

function handleVisualizationFileUpload(file) {
    visualizationFile = file;
    generateVisualizationBtn.style.display = 'block';
    showNotification('File uploaded. Configure your visualization and click Generate.');
}

generateVisualizationBtn.addEventListener('click', async () => {
    if (!visualizationFile) {
        showNotification('Please select a file first', 'error');
        return;
    }
    
    // Check if file is supported
    const fileExt = visualizationFile.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls', 'tsv'].includes(fileExt)) {
        showNotification('Only CSV, Excel, and TSV files are supported for visualization', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', visualizationFile);
    formData.append('chart_type', chartType.value);
    formData.append('x_column', xColumn.value);
    formData.append('y_column', yColumn.value);
    
    showLoading(visualizationResult);
    visualizationResult.style.display = 'block';
    
    try {
        console.log('Sending request to /api/data/visualize/');
        const response = await fetch(`${API_BASE_URL}/data/visualize/`, {
            method: 'POST',
            body: formData
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error('Error response:', errorData);
            throw new Error(errorData.detail || 'Visualization failed');
        }
        
        const result = await response.json();
        console.log('Visualization result:', result);
        
        // Create a container for the visualization
        const visualizationContainer = document.createElement('div');
        visualizationContainer.className = 'visualization-container';
        
        // Create the image element
        const img = document.createElement('img');
        img.src = result.image;
        img.alt = `Visualization: ${result.chart_type} chart of ${result.y_column} by ${result.x_column}`;
        img.style.maxWidth = '100%';
        img.style.height = 'auto';
        img.style.border = '1px solid #ddd';
        img.style.borderRadius = '4px';
        img.style.marginTop = '10px';
        
        // Create a download link
        const downloadLink = document.createElement('a');
        downloadLink.href = result.image;
        downloadLink.download = result.saved_filename;
        downloadLink.className = 'btn btn-primary';
        downloadLink.textContent = 'Download Visualization';
        downloadLink.style.marginTop = '10px';
        downloadLink.style.display = 'inline-block';
        
        // Create visualization info
        const infoDiv = document.createElement('div');
        infoDiv.innerHTML = `
            <h4>Visualization Details</h4>
            <p><strong>Chart Type:</strong> ${result.chart_type}</p>
            <p><strong>X-Axis:</strong> ${result.x_column}</p>
            <p><strong>Y-Axis:</strong> ${result.y_column}</p>
            <p><strong>File:</strong> ${result.filename}</p>
        `;
        infoDiv.style.marginTop = '10px';
        
        // Clear previous content and add new elements
        visualizationResult.innerHTML = '';
        visualizationResult.appendChild(infoDiv);
        visualizationResult.appendChild(img);
        visualizationResult.appendChild(downloadLink);
        
        showNotification('Visualization generated successfully!');
    } catch (error) {
        console.error('Visualization error:', error);
        visualizationResult.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        showNotification('Error generating visualization: ' + error.message, 'error');
    }
});

async function handleDataAnalysisUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add options based on user selections
    const generateActions = document.getElementById('generateActions').checked;
    const businessContext = document.getElementById('businessContext').value;
    const addToRag = document.getElementById('addToRag').checked;
    
    formData.append('generate_actions', generateActions);
    formData.append('business_context', businessContext);
    formData.append('add_to_rag', addToRag);
    
    showLoading(dataAnalysisResult);
    dataAnalysisResult.style.display = 'block';
    
    try {
        const response = await fetch(`${API_BASE_URL}/parse/`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Data analysis failed');
        }
        
        const result = await response.json();
        
        // Display the analysis results
        let html = `
            <h4>Data Analysis: ${result.filename}</h4>
            <div class="analysis-summary">
                <h5>Summary</h5>
                <p><strong>Rows:</strong> ${result.summary.rows}</p>
                <p><strong>Columns:</strong> ${result.summary.columns}</p>
                <p><strong>Column Names:</strong> ${result.summary.column_names.join(', ')}</p>
            </div>
        `;
        
        // Add KPIs if available
        if (result.kpis) {
            html += '<div class="kpi-section"><h5>KPIs</h5>';
            
            // Add statistics
            if (result.kpis.statistics) {
                html += '<h6>Statistical Summary</h6>';
                for (const [col, stats] of Object.entries(result.kpis.statistics)) {
                    html += `
                        <div class="stat-item">
                            <strong>${col}:</strong> 
                            Min: ${stats[0]}, 
                            Max: ${stats[1]}, 
                            Mean: ${stats[2]}, 
                            Median: ${stats[3]}, 
                            Std: ${stats[4]}
                        </div>
                    `;
                }
            }
            
            // Add categorical analysis
            if (result.kpis.categorical) {
                html += '<h6>Categorical Analysis</h6>';
                for (const [col, data] of Object.entries(result.kpis.categorical)) {
                    html += `
                        <div class="categorical-item">
                            <strong>${col}:</strong> 
                            ${data.unique_count} unique values
                        </div>
                    `;
                }
            }
            
            html += '</div>';
        }
        
        // Add trends if available
        if (result.trends && result.trends.length > 0) {
            html += '<div class="trends-section"><h5>Trends</h5>';
            for (const trend of result.trends) {
                const emoji = trend.trend === 'increasing' ? '📈' : 
                            trend.trend === 'decreasing' ? '📉' : '➡️';
                html += `
                    <div class="trend-item">
                        <strong>${trend.column}</strong> ${emoji}
                        <div>Trend: ${trend.trend}, Correlation: ${trend.correlation.toFixed(3)}</div>
                    </div>
                `;
            }
            html += '</div>';
        }
        
        // Add action items if available
        if (result.action_items && result.action_items.action_items) {
            html += '<div class="actions-section"><h5>Recommended Actions</h5>';
            for (const item of result.action_items.action_items) {
                const priorityEmoji = item.priority === 'high' ? '🔴' : 
                                    item.priority === 'medium' ? '🟡' : '🟢';
                html += `
                    <div class="action-item">
                        <div class="action-title">${priorityEmoji} ${item.title}</div>
                        <div class="action-details">
                            <strong>Category:</strong> ${item.category} | 
                            <strong>Priority:</strong> ${item.priority}
                        </div>
                        <div class="action-description">${item.description}</div>
                        <div class="action-meta">
                            <strong>Impact:</strong> ${item.expected_impact} | 
                            <strong>Timeline:</strong> ${item.timeline} | 
                            <strong>Responsible:</strong> ${item.responsible}
                        </div>
                    </div>
                `;
            }
            html += '</div>';
        }
        
        // Add RAG information if added to RAG
        if (result.rag_file_id) {
            html += `
                <div class="rag-info">
                    <h5>RAG Information</h5>
                    <p><strong>RAG File ID:</strong> ${result.rag_file_id}</p>
                    <p>This report has been added to the RAG system. You can now query it using the RAG chat interface.</p>
                </div>
            `;
        }
        
        dataAnalysisResult.innerHTML = html;
        
        showNotification('Data analysis completed successfully!');
        
        if (result.rag_file_id) {
            showNotification('Report added to RAG system successfully!');
        }
    } catch (error) {
        dataAnalysisResult.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        showNotification('Error analyzing data: ' + error.message, 'error');
        console.error('Data analysis error:', error);
    }
}
