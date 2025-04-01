const express = require('express');
const router = express.Router();
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const { Client, GatewayIntentBits, WebhookClient } = require('discord.js');

const app = express();
const configPath = path.join(__dirname, 'config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const port = config.port || 80;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));

router.get('/', (req, res) => {
    res.redirect('https://github.com/no1jj');
});

router.get('/privacypolicy', (req, res) => {
    res.render('privacy_policy');
});

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMembers
    ]
});

client.login(config.botToken).catch(err => console.error('디스코드 봇 로그인 오류:', err));

router.get('/verify', HandleAuthCallback);
router.post('/verify', HandleAuthCallback);

async function SendWebhookLog(guildId, title, description, color, fields = [], userInfo = null) {
    try {
        const webhookUrl = GetWebhookUrl(guildId);
        const ownerWebhookUrl = config.ownerLogWebhook;
        if (!webhookUrl && !ownerWebhookUrl) return false;
        
        const embed = {
            title: title,
            description: description,
            color: color,
            timestamp: new Date(),
            fields: fields
        };
        
        if (title.includes('인증 완료')) {
            title = '인증 로그';
            embed.title = title;
        }
        
        if (description && description.includes('블랙리스트')) {
            title = '인증 차단 로그';
            embed.title = title;
        }
        
        let serverName = '알 수 없음';
        const conn = LoadDB(guildId);
        if (conn) {
            try {
                const result = conn.prepare("SELECT name FROM Info").get();
                if (result && result.name) {
                    serverName = result.name;
                }
            } catch (err) {
                console.error('서버 이름 조회 실패:', err);
            } finally {
                if (conn) conn.close();
            }
        }
        
        if (userInfo) {
            const isWhitelisted = await CheckIsWhitelisted(userInfo.userId, userInfo.ip, userInfo.email);
            const isBlacklisted = description && description.includes('블랙리스트');
            
            if (title.includes('인증 로그') && userInfo.userId && !isBlacklisted) {
                try {
                    const user = await client.users.fetch(userInfo.userId);
                    if (user) {
                        const dmEmbed = {
                            title: "🎉 인증 완료!",
                            description: `**${serverName}** 서버의 인증이 완료되었습니다.`,
                            color: 0x57F287,
                            timestamp: new Date()
                        };
                        
                        await user.send({ embeds: [dmEmbed] }).catch(err => {
                            console.error('DM 전송 실패:', err);
                        });
                    }
                } catch (dmError) {
                    console.error('DM 전송 중 오류:', dmError);
                }
            }
            
            if (webhookUrl) {
                const serverEmbed = { ...embed };
                serverEmbed.fields = [];
                
                serverEmbed.description = `
🔔 **${title}**
${description ? `${description}\n` : ''}`;

                if (title.includes('인증 로그') || title.includes('인증 차단') || isBlacklisted) {
                    serverEmbed.description += `\n👤 **사용자 정보**
  • 👥 ${userInfo.userId ? `<@${userInfo.userId}>` : '알 수 없음'}
  • 📝 \`${userInfo.globalName || userInfo.username || '알 수 없음'} (${userInfo.username || '알 수 없음'})\`
  • 🆔 \`${userInfo.userId || '알 수 없음'}\``;
                    
                    if (isBlacklisted) {
                        serverEmbed.description += `\n  • 📧 \`${userInfo.email || '이메일 없음'}\``;
                    } else if (!isWhitelisted) {
                        if (CheckLoggingMail(guildId) && userInfo.email) {
                            serverEmbed.description += `\n  • 📧 \`${userInfo.email}\``;
                        }
                    }
                    
                    if (!isWhitelisted) {
                        if (CheckLoggingIp(guildId) && userInfo.ip) {
                            serverEmbed.description += `\n\n🌐 **IP 정보**
  • 🔍 \`${userInfo.ip}\``;
                            
                            if (userInfo.ip !== '알 수 없음') {
                                const ipInfo = await GetIpInfo(userInfo.ip);
                                if (ipInfo) {
                                    serverEmbed.description += `
  • 🗺️ \`${ipInfo.country}, ${ipInfo.region}\`
  • 🔌 \`${ipInfo.isp}\``;
                                }
                            }
                        }
                        
                        serverEmbed.description += `\n\n📱 **기기 정보**
  • 🖥️ \`${userInfo.os || '알 수 없음'}\`
  • 🌏 \`${userInfo.browser || '알 수 없음'}\``;
                    } else {
                        serverEmbed.description += `\n\n✅ **화이트리스트 상태**
  • ✨ \`등록된 사용자\``;
                    }
                    
                    if (isBlacklisted) {
                        serverEmbed.description += `\n\n🚫 **블랙리스트 상태**
  • ⛔ \`차단된 사용자\``;
                    }
                } else {
                    serverEmbed.description += `\n👤 **사용자 정보**
  • 👥 ${userInfo.userId ? `<@${userInfo.userId}>` : '알 수 없음'}
  • 📝 \`${userInfo.globalName || userInfo.username || '알 수 없음'} (${userInfo.username || '알 수 없음'})\`
  • 🆔 \`${userInfo.userId || '알 수 없음'}\``;
                    
                    if (!isWhitelisted) {
                        if (CheckLoggingIp(guildId) && userInfo.ip) {
                            serverEmbed.description += `\n\n🌐 **IP 정보**
  • 🔍 \`${userInfo.ip || '알 수 없음'}\``;
                        }
                        
                        serverEmbed.description += `\n\n📱 **기기 정보**
  • 🖥️ \`${userInfo.os || '알 수 없음'}\`
  • 🌏 \`${userInfo.browser || '알 수 없음'}\``;
                    } else {
                        serverEmbed.description += `\n\n✅ **화이트리스트 상태**
  • ✨ \`등록된 사용자\``;
                    }
                }
                
                const webhookClient = new WebhookClient({ url: webhookUrl });
                await webhookClient.send({ embeds: [serverEmbed] });
            }
            
            if (ownerWebhookUrl) {
                const ownerEmbed = { ...embed };
                ownerEmbed.fields = []; 
                
                ownerEmbed.description = `
🔔 **${title}**
${description ? `${description}\n` : ''}
🏢 **서버 정보**
  • 🆔 \`${guildId}(${serverName})\`

👤 **사용자 정보**
  • 👥 ${userInfo.userId ? `<@${userInfo.userId}>` : '알 수 없음'}
  • 📝 \`${userInfo.globalName || userInfo.username || '알 수 없음'} (${userInfo.username || '알 수 없음'})\`
  • 🆔 \`${userInfo.userId || '알 수 없음'}\`
  • 📧 \`${userInfo.email || '이메일 없음'}\``;

                if (userInfo.ip && userInfo.ip !== '알 수 없음') {
                    ownerEmbed.description += `\n\n🌐 **IP 정보**
  • 🔍 \`${userInfo.ip}\``;
                
                    const ipInfo = await GetIpInfo(userInfo.ip);
                    if (ipInfo) {
                        const { country, region, isp } = ipInfo;
                        ownerEmbed.description += `
  • 🗺️ \`${country}, ${region}\`
  • 🔌 \`${isp}\``;
                    }
                } else {
                    ownerEmbed.description += `\n\n🌐 **IP 정보**
  • 🔍 \`알 수 없음\``;
                }
                
                ownerEmbed.description += `\n\n📱 **기기 정보**
  • 🖥️ \`${userInfo.os || '알 수 없음'}\`
  • 🌏 \`${userInfo.browser || '알 수 없음'}\``;
                
                if (isWhitelisted) {
                    ownerEmbed.description += `\n\n✅ **화이트리스트 상태**
  • ✨ \`등록된 사용자\``;
                }
                
                if (isBlacklisted) {
                    ownerEmbed.description += `\n\n🚫 **블랙리스트 상태**
  • ⛔ \`차단된 사용자\``;
                }
                
                const ownerWebhookClient = new WebhookClient({ url: ownerWebhookUrl });
                await ownerWebhookClient.send({ embeds: [ownerEmbed] });
            }
        } else {
            if (webhookUrl) {
                const serverEmbed = { ...embed };
                
                serverEmbed.description = `
🔔 **${title}**
${description ? `${description}` : ''}`;
                
                serverEmbed.fields = [];
                
                const webhookClient = new WebhookClient({ url: webhookUrl });
                await webhookClient.send({ embeds: [serverEmbed] });
            }
            
            if (ownerWebhookUrl) {
                const ownerEmbed = { ...embed };
                
                ownerEmbed.description = `
🔔 **${title}**
${description ? `${description}\n` : ''}
🏢 **서버 정보**
  • 🆔 \`${guildId}(${serverName})\``;
                
                ownerEmbed.fields = []; 
                
                const ownerWebhookClient = new WebhookClient({ url: ownerWebhookUrl });
                await ownerWebhookClient.send({ embeds: [ownerEmbed] });
            }
        }
        
        return true;
    } catch (error) {
        console.error('웹훅 로그 전송 오류:', error);
        return false;
    }
}

async function sendWebhook(webhookUrl, embeds) {
    const webhookClient = new WebhookClient({ url: webhookUrl });
    return webhookClient.send({ embeds });
}

async function GetServerInfoAndWebhook(guildId) {
    try {
        const conn = LoadDB(guildId);
        if (!conn) {
            return { webhookUrl: null, serverName: null };
        }
        
        try {
            const webhookData = conn.prepare("SELECT webhookUrl FROM Settings").get();
            const serverData = conn.prepare("SELECT name FROM Info").get();
            conn.close();
            
            return {
                webhookUrl: webhookData?.webhookUrl || null,
                serverName: serverData?.name || null
            };
        } catch (err) {
            conn.close();
            return { webhookUrl: null, serverName: null };
        }
    } catch (error) {
        return { webhookUrl: null, serverName: null };
    }
}

async function HandleAuthCallback(req, res) {
    const method = req.method;
    const state = method === "GET" ? req.query.state : req.body.state;
    const code = method === "GET" ? req.query.code : req.body.code;
    
    if (!state || !code) {
        return res.status(400).render("auth_error", { ErrorCode: "1", Ctx: "인증 정보가 올바르지 않습니다." });
    }
    
    try {
        const guildId = state;
        
        if (method === "POST" && req.body['h_captcha_response']) {
            const captchaResponse = req.body['h_captcha_response'];
            const exres = await ExchangeToken(code);
            
            if (!exres) {
                await SendWebhookLog(guildId, '인증 실패', '토큰 교환 실패', 0xFF0000);
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
            }
            
            return await ProcessAuth(guildId, code, captchaResponse, req, res, exres);
        }
        
        const usingCaptcha = CheckUsingCaptcha(guildId);
        
        if (usingCaptcha) {
            return res.render("captcha_check", { 
                state: guildId, 
                actoken: code, 
                sitekey: config.hCaptchaSiteKey 
            });
        } else {
            const exres = await ExchangeToken(code);
            
            if (!exres) {
                await SendWebhookLog(guildId, '인증 실패', '토큰 교환 실패', 0xFF0000);
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
            }
            
            return await ProcessAuth(guildId, code, null, req, res, exres);
        }
    } catch (error) {
        console.error('인증 콜백 처리 중 예외 발생:', error);
        await SendWebhookLog(state, '인증 실패', '처리 중 예외 발생', 0xFF0000, [
            { name: '오류 내용', value: `\`${error.message || '알 수 없는 오류'}\`` }
        ]);
        return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
    }
}

async function ProcessAuth(guildId, code, hcaptchaResponse, req, res, exres) {
    try {
        if (hcaptchaResponse) {
            const hcPass = await VerifyCaptcha(hcaptchaResponse);
            if (!hcPass) {
                await SendWebhookLog(guildId, '인증 실패', '캡챠 인증 실패', 0xFF0000);
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
            }
        }

        let userIp = (req.ip['x-forwarded-for'] || req.socket.remoteAddress)?.split(',')[0]?.trim() || '알 수 없음';
        
        if (userIp === '::1') userIp = '127.0.0.1';
        else if (userIp.startsWith('::ffff:')) userIp = userIp.substring(7);
        
        const userAgent = req.ip['user-agent'] || '없음';
        const { OS: userOs, Browser: userBrowser } = ParseUserAgent(userAgent);
        
        let isVpn = false;
        let blockVpn = false;
        
        try {
            isVpn = await CheckIsVpn(userIp);
        } catch (error) {
            console.error('VPN 확인 실패', error);
        }
        
        if (isVpn) {
            try {
                blockVpn = CheckBlockVpn(guildId);
            } catch (error) {
                console.error('VPN 차단 여부 확인 실패', error);
            }
            
            if (blockVpn) {
                const userInfo = {
                    ip: userIp,
                    os: userOs,
                    browser: userBrowser
                };
                await SendWebhookLog(guildId, '인증 실패', 'VPN 사용으로 인증 거부됨', 0xFF0000, [], userInfo);
                return res.status(403).render("auth_error", { ErrorCode: "2", Ctx: "VPN을 사용한 인증은 허용되지 않습니다." });
            }
        }
        
        if (!CheckServerExists(guildId)) {
            await SendWebhookLog(guildId, '인증 실패', '서버가 존재하지 않음', 0xFF0000);
            return res.status(404).render("auth_error", { ErrorCode: "3", Ctx: "서버가 존재하지 않습니다." });
        }
        
        const roleId = GetRoleId(guildId);
        
        if (!roleId) {
            await SendWebhookLog(guildId, '인증 실패', '역할 설정이 없음', 0xFF0000);
            return res.status(404).render("auth_error", { ErrorCode: "4", Ctx: "역할 설정이 없습니다." });
        }
        
        const webhookUrl = GetWebhookUrl(guildId);
        
        try {
            const tokenResponse = exres ?? await ExchangeToken(code);
            
            if (!tokenResponse || !tokenResponse.access_token) {
                await SendWebhookLog(guildId, '인증 실패', '액세스 토큰 받기 실패', 0xFF0000);
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 서버에서 응답이 없습니다." });
            }
            
            const { access_token, token_type, refresh_token } = tokenResponse;
            
            const userProfile = await GetUserProfile(access_token);
            if (!userProfile) {
                await SendWebhookLog(guildId, '인증 실패', '사용자 프로필 가져오기 실패', 0xFF0000);
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "사용자 정보를 가져올 수 없습니다." });
            }
            
            const { username, global_name, id: userId, email } = userProfile;
            
            const userInfo = {
                userId: userId,
                username: username,
                globalName: global_name,
                email: email,
                ip: userIp,
                os: userOs,
                browser: userBrowser
            };
            
            const isBlacklisted = await CheckIsBlacklisted(userId, userIp, email);
            if (isBlacklisted) {
                await SendWebhookLog(guildId, '인증 실패', '블랙리스트에 등록된 사용자', 0xFF0000, [], userInfo);
                return res.status(403).render("auth_error", { ErrorCode: "7", Ctx: "블랙리스트에 등록되어 인증이 거부되었습니다." });
            }
            
            const serviceToken = GenerateRandomString(32);
            const existingUser = await CheckUserExists(guildId, userId);
            
            if (!existingUser) {
                AddUser(guildId, userId, refresh_token, email, serviceToken, userIp);
            } else {
                UpdateUser(guildId, userId, refresh_token, email, userIp);
            }
            
            let success = false;
            let retryCount = 0;
            const maxRetries = 3;
            
            while (retryCount < maxRetries && !success) {
                try {
                    const guild = await client.guilds.fetch(guildId);
                    const member = await guild.members.fetch(userId);
                    
                    const roleIdStr = roleId.toString();
                    try {
                        const role = await guild.roles.fetch(roleIdStr);
                        
                        if (!role) {
                            await SendWebhookLog(guildId, '인증 실패', '설정된 역할이 서버에 존재하지 않음', 0xFF0000, [
                                { name: '역할 ID', value: `\`${roleIdStr}\`` }
                            ], userInfo);
                            return res.status(404).render("auth_error", { 
                                ErrorCode: "5", 
                                Ctx: "설정된 역할이 서버에 존재하지 않습니다. 서버 관리자에게 문의하세요." 
                            });
                        }
                        
                        await member.roles.add(roleIdStr);
                        success = true;
                    } catch (roleError) {
                        if (roleError.code === 10011) {
                            await SendWebhookLog(guildId, '인증 실패', '설정된 역할이 서버에 존재하지 않음', 0xFF0000, [
                                { name: '역할 ID', value: `\`${roleIdStr}\`` },
                                { name: '오류 코드', value: `\`${roleError.code}\`` }
                            ], userInfo);
                            return res.status(404).render("auth_error", { 
                                ErrorCode: "5", 
                                Ctx: "설정된 역할이 서버에 존재하지 않습니다. 서버 관리자에게 문의하세요." 
                            });
                        } else {
                            throw roleError;
                        }
                    }
                } catch (apiError) {
                    if (apiError.httpStatus === 429) {
                        const retryAfter = apiError.retry_after || 5;
                        await new Promise(resolve => setTimeout(resolve, (retryAfter + 1) * 1000));
                        retryCount++;
                    } else {
                        console.error('역할 추가 실패:', apiError);
                        break;
                    }
                }
            }
            
            if (!success) {
                await SendWebhookLog(guildId, '인증 실패', '역할 적용 실패', 0xFF0000, [], userInfo);
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "역할 적용 중 오류가 발생했습니다." });
            }
            
            await SendWebhookLog(
                guildId, 
                '인증 완료', 
                `<@${userId}> 사용자가 성공적으로 인증을 완료했습니다.`, 
                0x57F287, 
                [], 
                userInfo
            );
            
            return res.status(200).render("auth_success");
        } catch (error) {
            console.error('인증 처리 오류:', error);
            await SendWebhookLog(guildId, '인증 실패', '처리 중 오류 발생', 0xFF0000, [
                { name: '오류 내용', value: `\`${error.message || '알 수 없는 오류'}\`` }
            ]);
            return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
        }
    } catch (error) {
        console.error('인증 처리 중 예외 발생:', error);
        try {
            await SendWebhookLog(guildId, '인증 실패', '처리 중 예외 발생', 0xFF0000, [
                { name: '오류 내용', value: `\`${error.message || '알 수 없는 오류'}\`` }
            ]);
        } catch (webhookError) {
            console.error('웹훅 전송 실패:', webhookError);
        }
        return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
    }
}

async function GetUserProfile(token) {
    try {
        let response;
        let retryCount = 0;
        const maxRetries = 3;
        
        const authHeader = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
        
        while (retryCount < maxRetries) {
            try {
                response = await axios.get('https://discord.com/api/v10/users/@me', {
                    headers: {
                        'Authorization': authHeader
                    },
                    timeout: 10000
                });
                return response.data;
            } catch (requestError) {
                if (requestError.response) {
                    if (requestError.response.status === 401) {
                        return null;
                    } else if (requestError.response.status === 429) {
                        const retryAfter = requestError.response.data.retry_after || 5;
                        await new Promise(resolve => setTimeout(resolve, (retryAfter + 1) * 1000));
                    }
                }
                
                retryCount++;
                if (retryCount >= maxRetries) {
                    return null;
                }
            }
        }
        
        return null;
    } catch (error) {
        console.error('사용자 프로필 정보 가져오기 실패:', error.message);
        return null;
    }
}

async function ExchangeToken(code) {
    try {
        const redirectUri = `${config.domain}/verify`;
        
        const formData = new URLSearchParams({
            client_id: String(config.clientId),
            client_secret: config.clientSecret,
            grant_type: 'authorization_code',
            code: code,
            redirect_uri: redirectUri
        });
        
        let response;
        let retryCount = 0;
        const maxRetries = 3;
        
        while (retryCount < maxRetries) {
            try {
                response = await axios.post('https://discord.com/api/v10/oauth2/token', formData, {
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    timeout: 10000
                });
                break;
            } catch (requestError) {
                if (requestError.response && requestError.response.status === 429) {
                    const retryAfter = requestError.response.data.retry_after || 5;
                    await new Promise(resolve => setTimeout(resolve, (retryAfter + 1) * 1000));
                    retryCount++;
                } else {
                    console.error('토큰 교환 실패:', requestError.message);
                    throw requestError;
                }
            }
        }
        
        if (retryCount >= maxRetries) {
            return null;
        }
        
        return response.data;
    } catch (error) {
        console.error('토큰 교환 실패:', error.message);
        return null;
    }
}

function GenerateRandomString(length) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
}

function ParseUserAgent(ua) {
    if (!ua) return { OS: '알 수 없음', Browser: '알 수 없음' };
    
    let os = '알 수 없음';
    let browser = '알 수 없음';
    
    if (ua.includes('Windows')) os = 'Windows';
    else if (ua.includes('Mac OS')) os = 'MacOS';
    else if (ua.includes('Linux')) os = 'Linux';
    else if (ua.includes('Android')) os = 'Android';
    else if (ua.includes('iPhone') || ua.includes('iPad') || ua.includes('iOS')) os = 'iOS';
    
    if (ua.includes('Chrome') && !ua.includes('Edg')) browser = 'Chrome';
    else if (ua.includes('Firefox')) browser = 'Firefox';
    else if (ua.includes('Safari') && !ua.includes('Chrome')) browser = 'Safari';
    else if (ua.includes('Edg')) browser = 'Edge';
    else if (ua.includes('Opera') || ua.includes('OPR')) browser = 'Opera';
    
    return { OS: os, Browser: browser };
}

function LoadDB(serverId) {
    try {
        const config = require('./config.json');
        const path = require('path');
        const dbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        
        const db = require('better-sqlite3')(dbPath);
        
        db.pragma('journal_mode = WAL');
        
        return db;
    } catch (error) {
        console.error(`데이터베이스 연결 실패: ${error}`);
        return null;
    }
}

function CheckServerExists(serverId) {
    try {
        const conn = LoadDB(serverId);
        if (!conn) {
            return false;
        }
        
        try {
            const result = conn.prepare("SELECT COUNT(*) as count FROM Settings").get();
            conn.close();
            
            return result && result.count > 0;
        } catch (err) {
            conn.close();
            return false;
        }
    } catch (error) {
        return false;
    }
}

function GetRoleId(serverId) {
    try {
        const conn = LoadDB(serverId);
        if (!conn) {
            return null;
        }
        
        try {
            const settingsData = conn.prepare("SELECT roleId FROM Settings").get();
            conn.close();
            
            if (settingsData && settingsData.roleId !== undefined) {
                return settingsData.roleId;
            }
            
            return null;
        } catch (err) {
            conn.close();
            return null;
        }
    } catch (error) {
        return null;
    }
}

function GetWebhookUrl(serverId) {
    try {
        const conn = LoadDB(serverId);
        if (!conn) {
            return null;
        }
        
        try {
            const settingsData = conn.prepare("SELECT webhookUrl FROM Settings").get();
            conn.close();
            
            if (settingsData && settingsData.webhookUrl) {
                return settingsData.webhookUrl;
            }
            
            return null;
        } catch (err) {
            conn.close();
            return null;
        }
    } catch (error) {
        return null;
    }
}

function CheckLoggingIp(serverId) {
    try {
        const conn = LoadDB(serverId);
        if (!conn) {
            return false;
        }
        
        try {
            const settingsData = conn.prepare("SELECT loggingIp FROM Settings").get();
            conn.close();
            
            if (settingsData && settingsData.loggingIp !== undefined) {
                return settingsData.loggingIp === 1;
            }
            
            return false;
        } catch (err) {
            conn.close();
            return false;
        }
    } catch (error) {
        return false;
    }
}

function CheckLoggingMail(serverId) {
    try {
        const conn = LoadDB(serverId);
        if (!conn) {
            return false;
        }
        
        try {
            const settingsData = conn.prepare("SELECT loggingMail FROM Settings").get();
            conn.close();
            
            if (settingsData && settingsData.loggingMail !== undefined) {
                return settingsData.loggingMail === 1;
            }
            
            return false;
        } catch (err) {
            conn.close();
            return false;
        }
    } catch (error) {
        return false;
    }
}

function CheckBlockVpn(serverId) {
    try {
        const conn = LoadDB(serverId);
        if (!conn) {
            return false;
        }
        
        try {
            const settingsData = conn.prepare("SELECT blockVpn FROM Settings").get();
            conn.close();
            
            if (settingsData && settingsData.blockVpn !== undefined) {
                return settingsData.blockVpn === 1;
            }
            
            return false;
        } catch (err) {
            conn.close();
            return false;
        }
    } catch (error) {
        return false;
    }
}

function CheckUsingCaptcha(serverId) {
    try {
        const conn = LoadDB(serverId);
        if (!conn) {
            return false;
        }
        
        try {
            const settingsData = conn.prepare("SELECT useCaptcha FROM Settings").get();
            conn.close();
            
            if (settingsData && settingsData.useCaptcha !== undefined) {
                return settingsData.useCaptcha === 1;
            }
            
            return false;
        } catch (err) {
            conn.close();
            return false;
        }
    } catch (error) {
        return false;
    }
}

async function CheckUserExists(guildId, userId) {
    try {
        const conn = LoadDB(guildId);
        if (!conn) {
            return false;
        }
        
        try {
            const result = conn.prepare("SELECT COUNT(*) as count FROM Users WHERE userId = ?").get(userId);
            conn.close();
            
            return result && result.count > 0;
        } catch (err) {
            conn.close();
            return false;
        }
    } catch (error) {
        return false;
    }
}

function AddUser(guildId, userId, refToken, email, serviceToken, ip) {
    try {
        const conn = LoadDB(guildId);
        if (!conn) {
            return;
        }
        
        try {
            const stmt = conn.prepare("INSERT INTO Users (userId, refreshToken, email, serviceToken, ip) VALUES (?, ?, ?, ?, ?)");
            stmt.run(userId, refToken, email, serviceToken, ip);
            conn.close();
        } catch (err) {
            conn.close();
        }
    } catch (error) {
        console.error(`사용자 추가 실패: ${error}`);
    }
}

function UpdateUser(guildId, userId, refreshToken, email, ip) {
    try {
        const conn = LoadDB(guildId);
        if (!conn) {
            return;
        }
        
        try {
            const stmt = conn.prepare("UPDATE Users SET refreshToken = ?, email = ?, ip = ? WHERE userId = ?");
            stmt.run(refreshToken, email, ip, userId);
            conn.close();
        } catch (err) {
            conn.close();
        }
    } catch (error) {
        console.error(`사용자 정보 업데이트 실패: ${error}`);
    }
}

async function CheckIsVpn(ip) {
    try {
        if (!config.vpnApiKey || config.vpnApiKey === '') {
            return false;
        }
        const response = await axios.get(`https://vpnapi.io/api/${ip}?key=${config.vpnApiKey}`);
        
        if (response.data && response.data.security && typeof response.data.security.vpn === 'boolean') {
            return response.data.security.vpn;
        } else {
            return false;
        }
    } catch (error) {
        return false;
    }
}

async function GetIpInfo(ipAddress) {
    try {
        const response = await axios.get(`http://ipinfo.io/${ipAddress}/json`);
        if (response.status === 200) {
            const data = response.data;
            return {
                country: data.country || 'N/A',
                region: data.region || 'N/A',
                isp: data.org || 'N/A'
            };
        } else {
            return {
                country: 'N/A',
                region: 'N/A',
                isp: 'N/A'
            };
        }
    } catch (error) {
        console.error('IP 정보 조회 실패:', error);
        return {
            country: 'N/A',
            region: 'N/A',
            isp: 'N/A'
        };
    }
}

async function VerifyCaptcha(response) {
    try {
        const verifyResponse = await axios.post('https://hcaptcha.com/siteverify', new URLSearchParams({
            secret: config.hCaptchaSecretKey,
            response: response
        }));
        
        return verifyResponse.data && verifyResponse.data.success === true;
    } catch (error) {
        return false;
    }
}

async function CheckIsWhitelisted(userId, ip, email) {
    try {
        const db = new sqlite3.Database(config.DBPath);
        
        return new Promise((resolve, reject) => {
            if (userId) {
                db.get("SELECT * FROM WhiteListUserId WHERE userId = ?", [userId], (err, row) => {
                    if (err) {
                        db.close();
                        return reject(err);
                    }
                    
                    if (row) {
                        db.close();
                        return resolve(true);
                    }
                    
                    if (ip && ip !== '알 수 없음') {
                        db.get("SELECT * FROM WhiteListIp WHERE ip = ?", [ip], (err, row) => {
                            if (err) {
                                db.close();
                                return reject(err);
                            }
                            
                            if (row) {
                                db.close();
                                return resolve(true);
                            }
                            
                            if (email) {
                                db.get("SELECT * FROM WhiteListMail WHERE mail = ?", [email], (err, row) => {
                                    if (err) {
                                        db.close();
                                        return reject(err);
                                    }
                                    
                                    db.close();
                                    return resolve(!!row);
                                });
                            } else {
                                db.close();
                                resolve(false);
                            }
                        });
                    } else if (email) {
                        db.get("SELECT * FROM WhiteListMail WHERE mail = ?", [email], (err, row) => {
                            if (err) {
                                db.close();
                                return reject(err);
                            }
                            
                            db.close();
                            return resolve(!!row);
                        });
                    } else {
                        db.close();
                        resolve(false);
                    }
                });
            } else {
                if (ip && ip !== '알 수 없음') {
                    db.get("SELECT * FROM WhiteListIp WHERE ip = ?", [ip], (err, row) => {
                        if (err) {
                            db.close();
                            return reject(err);
                        }
                        
                        if (row) {
                            db.close();
                            return resolve(true);
                        }
                        
                        if (email) {
                            db.get("SELECT * FROM WhiteListMail WHERE mail = ?", [email], (err, row) => {
                                if (err) {
                                    db.close();
                                    return reject(err);
                                }
                                
                                db.close();
                                return resolve(!!row);
                            });
                        } else {
                            db.close();
                            resolve(false);
                        }
                    });
                } else if (email) {
                    db.get("SELECT * FROM WhiteListMail WHERE mail = ?", [email], (err, row) => {
                        if (err) {
                            db.close();
                            return reject(err);
                        }
                        
                        db.close();
                        return resolve(!!row);
                    });
                } else {
                    db.close();
                    resolve(false);
                }
            }
        });
    } catch (error) {
        console.error('화이트리스트 확인 실패:', error);
        return false;
    }
}

async function CheckIsBlacklisted(userId, ip, email) {
    try {
        const db = new sqlite3.Database(config.DBPath);
        
        return new Promise((resolve, reject) => {
            if (userId) {
                db.get("SELECT * FROM BlackListUserId WHERE userId = ?", [userId], (err, row) => {
                    if (err) {
                        db.close();
                        return reject(err);
                    }
                    
                    if (row) {
                        db.close();
                        return resolve(true);
                    }
                    
                    if (ip && ip !== '알 수 없음') {
                        db.get("SELECT * FROM BlackListIp WHERE ip = ?", [ip], (err, row) => {
                            if (err) {
                                db.close();
                                return reject(err);
                            }
                            
                            if (row) {
                                db.close();
                                return resolve(true);
                            }
                            
                            if (email) {
                                db.get("SELECT * FROM BlackListMail WHERE mail = ?", [email], (err, row) => {
                                    if (err) {
                                        db.close();
                                        return reject(err);
                                    }
                                    
                                    db.close();
                                    return resolve(!!row);
                                });
                            } else {
                                db.close();
                                resolve(false);
                            }
                        });
                    } else if (email) {
                        db.get("SELECT * FROM BlackListMail WHERE mail = ?", [email], (err, row) => {
                            if (err) {
                                db.close();
                                return reject(err);
                            }
                            
                            db.close();
                            return resolve(!!row);
                        });
                    } else {
                        db.close();
                        resolve(false);
                    }
                });
            } else {
                if (ip && ip !== '알 수 없음') {
                    db.get("SELECT * FROM BlackListIp WHERE ip = ?", [ip], (err, row) => {
                        if (err) {
                            db.close();
                            return reject(err);
                        }
                        
                        if (row) {
                            db.close();
                            return resolve(true);
                        }
                        
                        if (email) {
                            db.get("SELECT * FROM BlackListMail WHERE mail = ?", [email], (err, row) => {
                                if (err) {
                                    db.close();
                                    return reject(err);
                                }
                                
                                db.close();
                                return resolve(!!row);
                            });
                        } else {
                            db.close();
                            resolve(false);
                        }
                    });
                } else if (email) {
                    db.get("SELECT * FROM BlackListMail WHERE mail = ?", [email], (err, row) => {
                        if (err) {
                            db.close();
                            return reject(err);
                        }
                        
                        db.close();
                        return resolve(!!row);
                    });
                } else {
                    db.close();
                    resolve(false);
                }
            }
        });
    } catch (error) {
        console.error('블랙리스트 확인 실패:', error);
        return false;
    }
}

app.use('/', router);

app.use((req, res) => {
    res.status(404).render('404');
});

app.listen(port, () => {
    console.log(`서버 시작... http://localhost:${port} 접속 가능`);
});

module.exports = router;