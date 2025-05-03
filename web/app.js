const express = require('express');
const path = require('path');
const fs = require('fs');
const { Client, GatewayIntentBits } = require('discord.js');
const session = require('express-session');
const csrf = require('csurf');
const flash = require('connect-flash');
const { check, validationResult } = require('express-validator');

const configPath = path.join(__dirname, '../config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

const app = express();
const port = config.port || 80;

const SESSION_SECRET = config.sessionSecret || 'restore_bot_secure_session_key';
const NODE_ENV = config.nodeEnv || 'development';

app.use(session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { 
        secure: NODE_ENV === 'production',
        maxAge: 3600000  // 1시간
    }
}));

app.use(flash());

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));

const csrfProtection = csrf({ cookie: false });

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMembers
    ]
});

client.login(config.botToken).catch(err => console.error('디스코드 봇 로그인 오류:', err));

app.set('discordClient', client);
app.set('config', config);
app.set('nodeEnv', NODE_ENV);

app.use((req, res, next) => {
    res.locals.success_messages = req.flash('success');
    res.locals.error_messages = req.flash('error');
    res.locals.isLoggedIn = req.session.loggedIn || false;
    next();
});

const indexRouter = require('./routes/index');
const authRouter = require('./routes/auth');
const settingRouter = require('./routes/setting');
const loginRouter = require('./routes/login');
const backupRouter = require('./routes/backup');

app.use('/', indexRouter);
app.use('/verify', authRouter);
app.use('/setting', settingRouter);
app.use('/backup', backupRouter);
app.use('/', loginRouter);

app.use((req, res) => {
    res.status(404).render('404');
});

app.use((err, req, res, next) => {
    console.error('서버 오류:', err);
    
    if (err.code === 'EBADCSRFTOKEN') {
        req.flash('error', '페이지를 새로고침하세요.');
        return res.redirect('back');
    }
    
    res.status(500).render('error', {
        message: '서버 오류가 발생했습니다.',
        error: NODE_ENV === 'development' ? err : {},
        settings: {
            nodeEnv: NODE_ENV
        }
    });
});

app.listen(port, () => {
    console.log(`웹 서버 시작... ${config.domain} 접속 가능 (포트: ${port})`);
});

module.exports = app; 

// V1.4