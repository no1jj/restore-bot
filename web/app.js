const express = require('express');
const path = require('path');
const fs = require('fs');
const { Client, GatewayIntentBits } = require('discord.js');

const configPath = path.join(__dirname, '../config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

const app = express();
const port = config.port || 80;

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

app.use('/', indexRouter);
app.use('/verify', authRouter);

app.use((req, res) => {
    res.status(404).render('404');
});

app.listen(port, () => {
    console.log(`웹 서버 시작... ${config.domain} 접속 가능`);
});

module.exports = app; 