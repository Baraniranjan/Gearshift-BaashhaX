const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');
const os = require('os');
const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// Serve static files (audio tracks, web app)
app.use(express.static('public'));

// Audio channels
const audioChannels = {
  'hindi': '/audio/hindi.mp3',
  'kannada': '/audio/kannada.mp3',
  'tamil': '/audio/tamil.mp3',
  // 'hindi': '/audio/movie_hindi.mp3'
};

let connectedUsers = 0

app.get('/api/ip', (req, res) => {
  const networkInterfaces = os.networkInterfaces();
  let localIP = 'localhost';

  Object.keys(networkInterfaces).forEach(interfaceName => {
    networkInterfaces[interfaceName].forEach(interface => {
      if (interface.family === 'IPv4' && !interface.internal) {
        localIP = interface.address;
      }
    });
  });

  res.send(localIP);
});

// Handle client connections
io.on('connection', (socket) => {
    connectedUsers++;
  console.log(`User connected: ${socket.id} (Total: ${connectedUsers})`);
    // Broadcast user count to all clients
  io.emit('user-count', connectedUsers);

  socket.on('join-channel', (language) => {
    console.log(`User ${socket.id} joined ${language} channel`);
    socket.join(language);
    socket.emit('audio-url', audioChannels[language]);
  });

  // FIX: Remove the duplicate sync-request handlers and the problematic one
  socket.on('sync-request', () => {
    console.log(`Sync requested by ${socket.id}`);
    // Forward sync request to the host (video player)
    socket.broadcast.emit('sync-requested', socket.id);
  });

  socket.on('video-play', (timestamp) => {
    console.log(`Broadcasting play at timestamp: ${timestamp}`);
    socket.broadcast.emit('video-play', timestamp);
  });

   socket.on('video-pause', (timestamp) => {
    console.log(`Broadcasting pause at timestamp: ${timestamp}`);
    socket.broadcast.emit('video-pause', timestamp);
  });

  socket.on('video-seek', (timestamp) => {
    console.log(`Broadcasting seek to timestamp: ${timestamp}`);
    socket.broadcast.emit('video-seek', timestamp);
  });

  socket.on('disconnect', () => {
    connectedUsers--;
    console.log(`User disconnected: ${socket.id} (Total: ${connectedUsers})`);
    io.emit('user-count', connectedUsers);
  });
});

server.listen(3001, '0.0.0.0', () => {
  console.log('✅ Server running on http://localhost:3001');
  console.log('📱 Mobile access: http://[YOUR-IP]:3001/client.html');
  console.log('🖥️  Host access: http://localhost:3001/host.html');
});