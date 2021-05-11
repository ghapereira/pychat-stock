var sessionId = '',
    token = '',
    x = '';

const baseURL = 'http://127.0.0.1:8000/v1';

function json(response) {
    x = response;
    return response.json();
}

var runlogin = async function() {
    let username = document.getElementById('username').value,
        password = document.getElementById('password').value,
        url = `${baseURL}/login`;

    const data = {"username": username, "password": password};

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });

    response.json().then(loginData => {
        sessionId = loginData.session_id;
        token = loginData.token;
        showAvailableChatrooms();
    });
};

var refreshChatroomMessages = async function() {
    let chatroomId = document.getElementById('chatroomId').innerText,
        username = document.getElementById('username').value,
        url = `${baseURL}/chatroom/${chatroomId}`;

    let chatroomMessages = document.getElementById('messages');

    chatroomMessages.innerHTML = '';

    const response = await fetch(url, {
        method: 'GET',
        headers: {
            'X-Token': token,
            'X-User': username,
            'X-SessionId': sessionId
        }
    });

    response.json().then(responseData => {
        for(message of responseData) {
            var node = document.createElement('div');
            node.innerText = message.text;
            chatroomMessages.appendChild(node);
        }
    });
};

var sendMessageToChatroom = async function() {
    let messageText = document.getElementById('postdiv').innerText;

    let chatroomId = document.getElementById('chatroomId').innerText,
        username = document.getElementById('username').value,
        url = `${baseURL}/chatroom/${chatroomId}`;

    const data = {'text': messageText};

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Token': token,
            'X-User': username,
            'X-SessionId': sessionId
        },
        body: JSON.stringify(data)
    });

    await refreshChatroomMessages();
};

var showAvailableChatrooms = async function() {
    let availableChatrooms = document.getElementById('availableChatrooms'),
        username = document.getElementById('username').value,
        url = `${baseURL}/chatroom`;

    availableChatrooms.innerHTML = '';

    const response = await fetch(url, {
        method: 'GET',
        headers: {
            'X-Token': token,
            'X-User': username,
            'X-SessionId': sessionId
        }
    });

    response.json().then(responseData => {
        for(message of responseData) {
            var node = document.createElement('div');
            node.innerText = message.uuid;
            node.onclick = function() {
                let chatroomId = document.getElementById('chatroomId');
                chatroomId.innerText = this.innerText;
                refreshChatroomMessages();
            };

            availableChatrooms.appendChild(node);
        }
    });
};
