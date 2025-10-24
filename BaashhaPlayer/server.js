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
  'english': '/audio/hindi.wav',
  'spanish': '/audio/kannada.wav',
  'french': '/audio/tamil.wav',
  'hindi': '/audio/movie_hindi.mp3'
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
    socket.join(language);
    socket.emit('audio-url', audioChannels[language]);
  });
socket.on('sync-request', () => {
    console.log(`Sync requested by ${socket.id}`);
    socket.broadcast.emit('sync-requested', socket.id);
  });

  socket.on('sync-request', () => {
    // Send current video timestamp
    socket.emit('sync-time', getCurrentVideoTime());
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
  console.log('Server running on http://[YOUR-IP]:3001');
});