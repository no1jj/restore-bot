const express = require('express');
const path = require('path');
const fs = require('fs');
const { Client, GatewayIntentBits } = require('discord.js');
const session = require('express-session');
const crypto = require('crypto');

const configPath = path.join(__dirname, '../config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

const app = express();
const port = config.port || 80;

app.use(session({
    secret: crypto.randomBytes(32).toString('hex'),
    resave: false,
    saveUninitialized: false,
    cookie: { 
        secure: process.env.NODE_ENV === 'production',
        maxAge: 3600000  // 1시간
    }
}));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMembers
    ]
});

client.login(config.botToken).catch(err => console.error('디스코드 봇 로그인 오류:', err));

app.set('discordClient', client);
app.set('config', config);

const indexRouter = require('./routes/index');
const authRouter = require('./routes/auth');
const settingRouter = require('./routes/setting');

app.use('/', indexRouter);
app.use('/verify', authRouter);
app.use('/login', authRouter);
app.use('/logout', authRouter);
app.use('/setting', settingRouter);

app.use((req, res) => {
    res.status(404).render('404');
});

app.listen(port, () => {
    console.log(`웹 서버 시작... ${config.domain} 접속 가능`);
});

module.exports = app; 