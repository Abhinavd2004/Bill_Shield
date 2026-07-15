// static/js/script.js
// Base URL for your Flask API
const API_BASE_URL = window.location.origin; // This will dynamically use the current origin (e.g., http://127.0.0.1:5000)

// --- Utility Functions ---
function showNotification(message, type = 'info') {
    const notificationsDiv = document.getElementById('notifications');
    const notification = document.createElement('div');
    notification.className = `notification ${type} mb-2`;
    notification.textContent = message;
    notificationsDiv.appendChild(notification);

    // Automatically remove notification after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

// --- User Authentication Logic ---
let currentUser = null; // Stores logged-in user info

async function checkUserStatus() {
    console.log('Checking user status...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/user_status`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include' // Important for sending session cookies
        });
        const data = await response.json();
        console.log('User status response:', data);

        if (data.isLoggedIn) {
            currentUser = data.user;
            document.getElementById('loggedInUsername').textContent = currentUser.username;
            document.getElementById('loggedOutView').classList.add('hidden');
            document.getElementById('loggedInView').classList.remove('hidden');
            document.getElementById('appContent').classList.remove('hidden');
            loadInitialData(); // Load user-specific data
        } else {
            currentUser = null;
            document.getElementById('loggedInView').classList.add('hidden');
            document.getElementById('loggedOutView').classList.remove('hidden');
            document.getElementById('appContent').classList.add('hidden');
            showNotification('Please log in or register to use the app.', 'info');
        }
    } catch (error) {
        console.error('Error checking user status:', error);
        showNotification('Failed to connect to authentication service. Please ensure backend is running.', 'error');
        currentUser = null;
        document.getElementById('loggedInView').classList.add('hidden');
        document.getElementById('loggedOutView').classList.remove('hidden');
        document.getElementById('appContent').classList.add('hidden');
    }
}

async function register() {
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;

    if (!username || !email || !password) {
        showNotification('Please fill in all registration fields.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password }),
            credentials: 'include'
        });
        const data = await response.json();

        if (response.ok) {
            showNotification(data.message + ' You are now logged in.', 'success');
            // Clear form
            document.getElementById('registerUsername').value = '';
            document.getElementById('registerEmail').value = '';
            document.getElementById('registerPassword').value = '';
            checkUserStatus(); // Update UI to logged-in state
        } else {
            showNotification(data.error || 'Registration failed.', 'error');
        }
    } catch (error) {
        console.error('Error during registration:', error);
        showNotification('Failed to connect to backend for registration. Check console.', 'error');
    }
}

async function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    if (!username || !password) {
        showNotification('Please enter username and password.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password }),
            credentials: 'include'
        });
        const data = await response.json();

        if (response.ok) {
            showNotification(data.message, 'success');
            // Clear form
            document.getElementById('loginUsername').value = '';
            document.getElementById('loginPassword').value = '';
            checkUserStatus(); // Update UI to logged-in state
        } else {
            showNotification(data.error || 'Login failed.', 'error');
        }
    } catch (error) {
        console.error('Error during login:', error);
        showNotification('Failed to connect to backend for login. Check console.', 'error');
    }
}

async function logout() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/logout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        const data = await response.json();

        if (response.ok) {
            showNotification(data.message, 'info');
            checkUserStatus(); // Update UI to logged-out state
        } else {
            showNotification(data.error || 'Logout failed.', 'error');
        }
    } catch (error) {
        console.error('Error during logout:', error);
        showNotification('Failed to connect to backend for logout. Check console.', 'error');
    }
}


// --- Bill Tracker Logic ---
let currentTargetAmount = 0; // Will be fetched from backend
let bills = []; // Will be fetched from backend

async function loadInitialData() {
    console.log('Loading initial data...');
    // Only load data if user is logged in
    if (!currentUser) {
        console.log('Not logged in, skipping initial data load.');
        return;
    }

    try {
        // Fetch target amount
        const targetResponse = await fetch(`${API_BASE_URL}/api/target`, { credentials: 'include' });
        if (targetResponse.status === 401) { await handleAuthError(); return; }
        const targetData = await targetResponse.json();
        currentTargetAmount = targetData.targetAmount;
        updateTargetDisplay();
        console.log('Target amount loaded:', currentTargetAmount);


        // Fetch bills
        const billsResponse = await fetch(`${API_BASE_URL}/api/bills`, { credentials: 'include' });
        if (billsResponse.status === 401) { await handleAuthError(); return; }
        const billsData = await billsResponse.json();
        bills = billsData;
        displayBills();
        console.log('Bills loaded:', bills);


        // Fetch warranties
        const warrantiesResponse = await fetch(`${API_BASE_URL}/api/warranties`, { credentials: 'include' });
        if (warrantiesResponse.status === 401) { await handleAuthError(); return; }
        const warrantiesData = await warrantiesResponse.json();
        warranties = warrantiesData;
        displayWarranties();
        console.log('Warranties loaded:', warranties);


        // Perform initial warranty check
        checkWarranties();

    } catch (error) {
        console.error('Error loading initial data:', error);
        showNotification('Failed to load initial data. Please ensure the backend is running and you are logged in.', 'error');
    }
}

function updateTargetDisplay() {
    document.getElementById('currentTarget').textContent = `Current Target: ₹ ${currentTargetAmount.toFixed(2)}`;
}

async function setTargetAmount() {
    if (!currentUser) { showNotification('Please log in to set a target.', 'warning'); return; }

    const input = document.getElementById('targetAmount');
    const amount = parseFloat(input.value);
    if (isNaN(amount) || amount < 0) {
        showNotification('Please enter a valid positive target amount.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/target`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ amount: amount }),
            credentials: 'include'
        });

        if (response.status === 401) { await handleAuthError(); return; }

        const data = await response.json();

        if (response.ok) {
            currentTargetAmount = data.targetAmount;
            updateTargetDisplay();
            showNotification(data.message, 'success');
            input.value = '';
        } else {
            showNotification(data.error || 'Failed to set target amount.', 'error');
        }
    } catch (error) {
        console.error('Error setting target amount:', error);
        showNotification('Failed to connect to the backend to set target amount. Check console for details.', 'error');
    }
}

async function addBill() {
    if (!currentUser) { showNotification('Please log in to add a bill.', 'warning'); return; }

    const billAmountInput = document.getElementById('billAmount');
    const billDateInput = document.getElementById('billDate');

    const amount = parseFloat(billAmountInput.value);
    const date = billDateInput.value;

    if (isNaN(amount) || amount <= 0 || !date) {
        showNotification('Please enter a valid positive bill amount and select a date.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/bills`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ amount: amount, date: date }),
            credentials: 'include'
        });

        if (response.status === 401) { await handleAuthError(); return; }

        const data = await response.json();

        if (response.ok) {
            showNotification(data.message, 'success');
            billAmountInput.value = '';
            billDateInput.value = '';
            // Re-fetch bills to ensure UI is in sync with backend
            const billsResponse = await fetch(`${API_BASE_URL}/api/bills`, { credentials: 'include' });
            if (billsResponse.status === 401) { await handleAuthError(); return; }
            const billsData = await billsResponse.json();
            bills = billsData;
            displayBills();
        } else {
            showNotification(data.error || 'Failed to add bill. Check backend logs.', 'error');
        }
    } catch (error) {
        console.error('Error adding bill:', error);
        showNotification('Failed to connect to the backend to add bill. Check console for details.', 'error');
    }
}

async function deleteBill(id) {
    if (!currentUser) { showNotification('Please log in to delete a bill.', 'warning'); return; }

    // Using a custom modal/dialog for confirmation instead of browser's confirm()
    const userConfirmed = await new Promise(resolve => {
        const confirmDialog = document.createElement('div');
        confirmDialog.className = 'fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50';
        confirmDialog.innerHTML = `
            <div class="bg-gray-800 p-6 rounded-lg shadow-xl text-center max-w-sm">
                <p class="text-lg text-gray-200 mb-4">Are you sure you want to delete this bill?</p>
                <div class="flex justify-center gap-4">
                    <button id="confirmDeleteBtn" class="btn btn-primary">Yes, Delete</button>
                    <button id="cancelDeleteBtn" class="btn btn-secondary">Cancel</button>
                </div>
            </div>
        `;
        document.body.appendChild(confirmDialog);

        document.getElementById('confirmDeleteBtn').onclick = () => {
            confirmDialog.remove();
            resolve(true);
        };
        document.getElementById('cancelDeleteBtn').onclick = () => {
            confirmDialog.remove();
            resolve(false);
        };
    });

    if (!userConfirmed) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/bills/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (response.status === 401) { await handleAuthError(); return; }

        const data = await response.json();

        if (response.ok) {
            showNotification(data.message, 'success');
            const billsResponse = await fetch(`${API_BASE_URL}/api/bills`, { credentials: 'include' });
            if (billsResponse.status === 401) { await handleAuthError(); return; }
            const billsData = await billsResponse.json();
            bills = billsData;
            displayBills();
        } else {
            showNotification(data.error || 'Failed to delete bill.', 'error');
        }
    } catch (error) {
        console.error('Error deleting bill:', error);
        showNotification('Failed to connect to the backend to delete bill. Check console for details.', 'error');
    }
}

function displayBills() {
    console.log('Displaying bills:', bills);
    const billListDiv = document.getElementById('billList');
    billListDiv.innerHTML = '';
    document.getElementById('noBillsMessage').style.display = bills.length === 0 ? 'block' : 'none';

    bills.forEach(bill => {
        const billItem = document.createElement('div');
        billItem.className = 'list-item text-gray-300';
        billItem.innerHTML = `
            <span>₹ ${bill.amount.toFixed(2)} on ${formatDate(bill.bill_date)}</span>
            <button class="delete-btn" onclick="deleteBill(${bill.id})">🗑️</button>
        `;
        billListDiv.appendChild(billItem);
    });
}

async function checkSpending() {
    if (!currentUser) { showNotification('Please log in to check spending.', 'warning'); return; }

    const timeFrame = parseInt(document.getElementById('timeFrame').value);

    try {
        const response = await fetch(`${API_BASE_URL}/api/spending?timeFrame=${timeFrame}`, { credentials: 'include' });

        if (response.status === 401) { await handleAuthError(); return; }

        const data = await response.json();

        if (response.ok) {
            document.getElementById('totalSpending').textContent = `Total spending in selected period: ₹ ${data.totalSpending.toFixed(2)}`;
            showNotification(data.message, data.notificationType);
            currentTargetAmount = data.targetAmount;
            updateTargetDisplay();
        } else {
            showNotification(data.error || 'Failed to check spending.', 'error');
        }
    } catch (error) {
        console.error('Error checking spending:', error);
        showNotification('Failed to connect to the backend to check spending. Check console for details.', 'error');
    }
}

// --- Bill Photo Upload Logic ---
async function uploadBillPhoto() {
    if (!currentUser) { showNotification('Please log in to upload a bill photo.', 'warning'); return; }

    const billPhotoInput = document.getElementById('billPhoto');
    const file = billPhotoInput.files[0];
    const loadingSpinner = document.getElementById('loadingSpinner');

    if (!file) {
        showNotification('Please select an image file to upload.', 'error');
        return;
    }

    loadingSpinner.classList.remove('hidden');

    const reader = new FileReader();
    reader.onloadend = async () => {
        const base64data = reader.result.split(',')[1];

        try {
            const response = await fetch(`${API_BASE_URL}/api/bills/upload`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ imageData: base64data, mimeType: file.type }),
                credentials: 'include'
            });

            if (response.status === 401) { await handleAuthError(); return; }

            const data = await response.json();

            if (response.ok) {
                if (data.extractedAmount !== null) {
                    document.getElementById('billAmount').value = data.extractedAmount;
                    showNotification(`Bill amount detected: ₹ ${data.extractedAmount}. Please verify and add bill.`, 'success');
                } else {
                    showNotification('Could not detect a bill amount from the photo. Please enter manually.', 'warning');
                }
                if (data.extractedDate) {
                    document.getElementById('billDate').value = data.extractedDate;
                }
            } else {
                showNotification(data.error || 'Failed to process bill photo. Check backend logs.', 'error');
            }
        } catch (error) {
            console.error('Error uploading bill photo:', error);
            showNotification('Failed to connect to the backend or process photo. Check console for details.', 'error');
        } finally {
            loadingSpinner.classList.add('hidden');
            billPhotoInput.value = '';
        }
    };
    reader.readAsDataURL(file);
}


// --- Warranty Tracker Logic ---
let warranties = []; // Will be fetched from backend

async function addWarranty() {
    if (!currentUser) { showNotification('Please log in to add a warranty.', 'warning'); return; }

    const warrantyItemInput = document.getElementById('warrantyItem');
    const warrantyEndDateInput = document.getElementById('warrantyEndDate');

    const item = warrantyItemInput.value.trim();
    const endDate = warrantyEndDateInput.value;

    if (!item || !endDate) {
        showNotification('Please enter both item name and warranty end date.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/warranties`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ item: item, endDate: endDate }),
            credentials: 'include'
        });

        if (response.status === 401) { await handleAuthError(); return; } // Handle 401 specifically

        const data = await response.json();

        if (response.ok) {
            showNotification(data.message, 'success');
            warrantyItemInput.value = '';
            warrantyEndDateInput.value = '';
            // Re-fetch warranties to ensure UI is in sync with backend
            const warrantiesResponse = await fetch(`${API_BASE_URL}/api/warranties`, { credentials: 'include' });
            if (warrantiesResponse.status === 401) { await handleAuthError(); return; }
            const warrantiesData = await warrantiesResponse.json();
            warranties = warrantiesData;
            displayWarranties();
        } else {
            showNotification(data.error || 'Failed to add warranty.', 'error');
        }
    } catch (error) {
        console.error('Error adding warranty:', error);
        showNotification('Failed to connect to the backend to add warranty. Check console for details.', 'error');
    }
}

async function deleteWarranty(id) {
    if (!currentUser) { showNotification('Please log in to delete a warranty.', 'warning'); return; }

    const userConfirmed = await new Promise(resolve => {
        const confirmDialog = document.createElement('div');
        confirmDialog.className = 'fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50';
        confirmDialog.innerHTML = `
            <div class="bg-gray-800 p-6 rounded-lg shadow-xl text-center max-w-sm">
                <p class="text-lg text-gray-200 mb-4">Are you sure you want to delete this warranty?</p>
                <div class="flex justify-center gap-4">
                    <button id="confirmDeleteBtn" class="btn btn-primary">Yes, Delete</button>
                    <button id="cancelDeleteBtn" class="btn btn-secondary">Cancel</button>
                </div>
            </div>
        `;
        document.body.appendChild(confirmDialog);

        document.getElementById('confirmDeleteBtn').onclick = () => {
            confirmDialog.remove();
            resolve(true);
        };
        document.getElementById('cancelDeleteBtn').onclick = () => {
            confirmDialog.remove();
            resolve(false);
        };
    });

    if (!userConfirmed) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/warranties/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (response.status === 401) { await handleAuthError(); return; }

        const data = await response.json();

        if (response.ok) {
            showNotification(data.message, 'success');
            const warrantiesResponse = await fetch(`${API_BASE_URL}/api/warranties`, { credentials: 'include' });
            if (warrantiesResponse.status === 401) { await handleAuthError(); return; }
            const warrantiesData = await warrantiesResponse.json();
            warranties = warrantiesData;
            displayWarranties();
        } else {
            showNotification(data.error || 'Failed to delete warranty.', 'error');
        }
    } catch (error) {
        console.error('Error deleting warranty:', error);
        showNotification('Failed to connect to the backend to delete warranty. Check console for details.', 'error');
    }
}

function displayWarranties() {
    console.log('Displaying warranties:', warranties);
    const warrantyListDiv = document.getElementById('warrantyList');
    warrantyListDiv.innerHTML = '';
    document.getElementById('noWarrantiesMessage').style.display = warranties.length === 0 ? 'block' : 'none';

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    warranties.forEach(warranty => {
        const warrantyItem = document.createElement('div');
        warrantyItem.className = 'list-item text-gray-300';
        const endDate = new Date(warranty.end_date);
        endDate.setHours(0, 0, 0, 0);

        let statusText = '';
        let statusClass = '';

        if (endDate < today) {
            statusText = ' (Expired)';
            statusClass = 'text-red-400 font-semibold';
        } else {
            const daysRemaining = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));
            if (daysRemaining <= 30) {
                statusText = ` (${daysRemaining} days left)`;
                statusClass = 'text-orange-400 font-semibold';
            } else {
                statusText = '';
                statusClass = '';
            }
        }

        warrantyItem.innerHTML = `
            <span>${warranty.item_name}: <span class="${statusClass}">${formatDate(warranty.end_date)}${statusText}</span></span>
            <button class="delete-btn" onclick="deleteWarranty(${warranty.id})">🗑️</button>
        `;
        warrantyListDiv.appendChild(warrantyItem);
    });
}

async function checkWarranties() {
    if (!currentUser) { showNotification('Please log in to check warranties.', 'warning'); return; }

    try {
        const response = await fetch(`${API_BASE_URL}/api/warranties/check`, { credentials: 'include' });

        if (response.status === 401) { await handleAuthError(); return; }

        const data = await response.json();

        if (response.ok) {
            document.getElementById('notifications').innerHTML = ''; // Clear previous notifications
            data.notifications.forEach(notification => {
                showNotification(notification.message, notification.type);
            });
            const warrantiesResponse = await fetch(`${API_BASE_URL}/api/warranties`, { credentials: 'include' });
            if (warrantiesResponse.status === 401) { await handleAuthError(); return; }
            const warrantiesData = await warrantiesResponse.json();
            warranties = warrantiesData;
            displayWarranties();
        } else {
            showNotification(data.error || 'Failed to check warranties.', 'error');
        }
    } catch (error) {
        console.error('Error checking warranties:', error);
        showNotification('Failed to connect to the backend to check warranties. Check console for details.', 'error');
    }
}

// Handles 401 Unauthorized responses
async function handleAuthError() {
    showNotification('Your session has expired or you are not logged in. Please log in again.', 'error');
    await logout(); // Force logout on frontend to clear state
    checkUserStatus(); // Redirect to login view
}

// --- Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
    checkUserStatus(); // Check login status on page load
});

