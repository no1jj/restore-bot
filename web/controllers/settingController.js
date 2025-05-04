const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const { promisify } = require('util');
const { ChannelType, PermissionFlagsBits } = require('discord.js');
const axios = require('axios');

/**
 * 데이터베이스 연결 및 쿼리 Promise 래퍼
 * @param {string} dbPath - 데이터베이스 경로
 * @returns {Object} - Promise 기반 쿼리 메서드가 있는 객체
 */
function getDb(dbPath) {
    const db = new sqlite3.Database(dbPath);
    
    return {
        get: promisify(db.get.bind(db)),
        run: promisify(db.run.bind(db)),
        all: promisify(db.all.bind(db)),
        close: () => {
            return new Promise((resolve, reject) => {
                db.close(err => {
                    if (err) return reject(err);
                    resolve();
                });
            });
        }
    };
}

/**
 * 설정 페이지 렌더링
 */
exports.renderSettingPage = async (req, res) => {
    let db = null;
    
    try {
        const config = req.app.get('config');
        const discordClient = req.app.get('discordClient');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            req.flash('error', '세션이 만료되었습니다. 다시 로그인해주세요.');
            return res.redirect('/login');
        }
        
        const guild = await discordClient.guilds.fetch(serverId).catch(() => null);
        if (!guild) {
            req.flash('error', '봇이 서버에 접근할 수 없습니다. 봇이 서버에 초대되어 있는지 확인하세요.');
            return res.redirect('/login');
        }
        
        const serverDbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        db = getDb(serverDbPath);
        
        const serverInfo = await db.get("SELECT * FROM Info");
        
        if (!serverInfo) {
            req.flash('error', '서버 정보를 찾을 수 없습니다.');
            return res.redirect('/login');
        }
        
        if (!serverInfo.serverId) {
            serverInfo.serverId = serverId;
        }
        
        const settings = await db.get("SELECT * FROM Settings");
        
        if (!settings) {
            req.flash('error', '설정 정보를 찾을 수 없습니다.');
            return res.redirect('/login');
        }
        
        const roles = await guild.roles.fetch();
        const roleList = roles.filter(role => 
            role.id !== serverId && 
            !role.managed &&
            role.name !== '@everyone'
        ).sort((a, b) => b.position - a.position) 
        .map(role => ({
            id: role.id,
            name: role.name,
            color: role.hexColor
        }));
        
        const channels = await guild.channels.fetch();
        const textChannels = channels.filter(channel => 
            channel.type === ChannelType.GuildText && 
            channel.permissionsFor(guild.members.me).has([
                PermissionFlagsBits.ViewChannel, 
                PermissionFlagsBits.SendMessages
            ])
        ).sort((a, b) => a.position - b.position)
        .map(channel => ({
            id: channel.id,
            name: channel.name,
            parentName: channel.parent ? channel.parent.name : '없음'
        }));
        
        const formattedSettings = {
            loggingIp: settings.loggingIp === 1,
            loggingMail: settings.loggingMail === 1,
            webhookUrl: settings.webhookUrl || '',
            roleId: settings.roleId || '',
            useCaptcha: settings.useCaptcha === 1,
            blockVpn: settings.blockVpn === 1,
            loggingChannelId: settings.loggingChannelId || ''
        };
        
        res.render('setting_panel', {
            serverInfo: {
                ...serverInfo,
                iconURL: guild.iconURL({ dynamic: true }) || null
            },
            settings: formattedSettings,
            csrfToken: req.csrfToken(),
            roles: roleList,
            channels: textChannels
        });
    } catch (error) {
        console.error('설정 페이지 렌더링 오류:', error);
        req.flash('error', '설정 정보를 불러오는 중 오류가 발생했습니다.');
        res.redirect('/login');
    } finally {
        if (db) {
            try {
                await db.close();
            } catch (err) {
                console.error('데이터베이스 연결 종료 오류:', err);
            }
        }
    }
};

/**
 * 설정 값 유효성 검사
 * @param {Object} settings - 검사할 설정 객체
 * @returns {Object} - 검증된 설정 객체
 */
function validateSettings(settings) {
    if (settings.roleId && !/^\d+$/.test(settings.roleId)) {
        settings.roleId = '0';
    }
    
    if (settings.loggingChannelId && !/^\d+$/.test(settings.loggingChannelId)) {
        settings.loggingChannelId = '0';
    }
    
    return settings;
}

/**
 * 웹훅 생성 또는 가져오기
 * @param {object} guild - 디스코드 서버 객체
 * @param {string} channelId - 채널 ID
 * @returns {string} - 웹훅 URL
 */
async function createOrGetWebhook(guild, channelId) {
    try {
        if (!channelId || channelId === '0') return '';
        
        const channel = await guild.channels.fetch(channelId);
        if (!channel) return '';
        
        const webhooks = await channel.fetchWebhooks();
        const existingWebhook = webhooks.find(webhook => webhook.name === 'RestoreBot');
        if (existingWebhook) {
            return existingWebhook.url;
        }

        const avatarUrl = 'https://cdn.discordapp.com/icons/1337624999380521030/c9d449b5f7d72d82cfc68e3d5e080820.webp?size=1024';
        const avatarData = await axios.get(avatarUrl, { responseType: 'arraybuffer' });
        const avatarBase64 = Buffer.from(avatarData.data).toString('base64');
        const mimeType = 'image/webp'; 
        const avatar = `data:${mimeType};base64,${avatarBase64}`;

        const newWebhook = await channel.createWebhook({
            name: 'RestoreBot',
            avatar: avatar
        });
        
        return newWebhook.url;
    } catch (error) {
        console.error('웹훅 생성 오류:', error);
        return '';
    }
}

/**
 * 설정 업데이트
 */
exports.updateSettings = async (req, res) => {
    let db = null;
    
    try {
        const config = req.app.get('config');
        const discordClient = req.app.get('discordClient');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            req.flash('error', '세션이 만료되었습니다. 다시 로그인해주세요.');
            return res.redirect('/login');
        }
        
        const guild = await discordClient.guilds.fetch(serverId).catch(() => null);
        if (!guild) {
            req.flash('error', '봇이 서버에 접근할 수 없습니다.');
            return res.redirect('/setting');
        }
        
        const serverDbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        db = getDb(serverDbPath);
        
        const loggingChannelId = req.body.loggingChannelId || '0';
        let webhookUrl = '';
        
        if (loggingChannelId !== '0') {
            webhookUrl = await createOrGetWebhook(guild, loggingChannelId);
        }
        
        const settings = {
            loggingIp: req.body.loggingIp ? 1 : 0,
            loggingMail: req.body.loggingMail ? 1 : 0,
            webhookUrl: webhookUrl,
            roleId: req.body.roleId || '0',
            useCaptcha: req.body.useCaptcha ? 1 : 0,
            blockVpn: req.body.blockVpn ? 1 : 0,
            loggingChannelId: loggingChannelId
        };
        
        const validatedSettings = validateSettings(settings);
        
        await db.run(`
            UPDATE Settings SET 
            loggingIp = ?, 
            loggingMail = ?, 
            webhookUrl = ?, 
            roleId = ?, 
            useCaptcha = ?, 
            blockVpn = ?,
            loggingChannelId = ?
        `, [
            validatedSettings.loggingIp,
            validatedSettings.loggingMail,
            validatedSettings.webhookUrl,
            validatedSettings.roleId,
            validatedSettings.useCaptcha,
            validatedSettings.blockVpn,
            validatedSettings.loggingChannelId
        ]);
        
        req.flash('success', '설정이 성공적으로 저장되었습니다.');
        res.redirect('/setting');
    } catch (error) {
        console.error('설정 업데이트 오류:', error);
        req.flash('error', '설정을 저장하는 중 오류가 발생했습니다.');
        res.redirect('/setting');
    } finally {
        if (db) {
            try {
                await db.close();
            } catch (err) {
                console.error('데이터베이스 연결 종료 오류:', err);
            }
        }
    }
};

/**
 * 인증 메시지 전송
 */
exports.sendAuthMessage = async (req, res) => {
    let db = null;
    
    try {
        const config = req.app.get('config');
        const discordClient = req.app.get('discordClient');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            return res.json({ success: false, message: '세션이 만료되었습니다. 다시 로그인해주세요.' });
        }
        
        const { channelId, title, description, buttonText } = req.body;
        
        if (!channelId || channelId === '0') {
            return res.json({ success: false, message: '채널을 선택해주세요.' });
        }
        
        const guild = await discordClient.guilds.fetch(serverId).catch(() => null);
        if (!guild) {
            return res.json({ success: false, message: '봇이 서버에 접근할 수 없습니다.' });
        }
        
        const channel = await guild.channels.fetch(channelId).catch(() => null);
        if (!channel) {
            return res.json({ success: false, message: '선택한 채널을 찾을 수 없습니다.' });
        }
        
        const serverDbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        db = getDb(serverDbPath);
        
        const settings = await db.get("SELECT roleId FROM Settings");
        
        if (!settings || !settings.roleId) {
            return res.json({ success: false, message: '인증 역할이 설정되어 있지 않습니다. 먼저 설정 페이지에서 인증 역할을 설정해주세요.' });
        }
        
        try {
            const embed = {
                title: title || '서버 인증',
                description: description || '아래 버튼을 클릭하여 서버 인증을 완료해주세요.',
                color: 0x2ecc71, // 녹색
                timestamp: new Date()
            };
            
            const row = {
                type: 1,
                components: [
                    {
                        type: 2,
                        style: 3, 
                        label: buttonText || '인증하기',
                        custom_id: `Sauth_button`
                    }
                ]
            };
            
            await channel.send({ embeds: [embed], components: [row] });
            
            return res.json({ 
                success: true, 
                message: '인증 메시지가 성공적으로 전송되었습니다.',
                roleId: settings.roleId
            });
        } catch (error) {
            console.error('인증 메시지 전송 오류:', error);
            return res.json({ success: false, message: `인증 메시지 전송 중 오류가 발생했습니다: ${error.message}` });
        }
    } catch (error) {
        console.error('인증 메시지 처리 오류:', error);
        return res.json({ success: false, message: '오류가 발생했습니다.' });
    } finally {
        if (db) {
            try {
                await db.close();
            } catch (err) {
                console.error('데이터베이스 연결 종료 오류:', err);
            }
        }
    }
};

/**
 * 디스코드 사용자 정보 가져오기
 * @param {string} userId - 디스코드 사용자 ID
 * @param {object} discordClient - 디스코드 클라이언트 객체
 * @returns {Promise<object>} - 사용자 정보 객체 (없으면 null)
 */
async function fetchUserInfo(userId, discordClient) {
    try {
        if (!userId || userId === '-') return null;
        
        const user = await discordClient.users.fetch(userId).catch(() => null);
        if (!user) return null;
        
        return {
            id: user.id,
            username: user.username,
            displayName: user.globalName || user.username,
            formattedName: `${user.globalName || user.username}(${user.username})(${user.id})`
        };
    } catch (error) {
        console.error('사용자 정보 조회 오류:', error);
        return null;
    }
}

/**
 * 인증 로그 목록 조회
 */
exports.getLogs = async (req, res) => {
    let db = null;
    
    try {
        const config = req.app.get('config');
        const discordClient = req.app.get('discordClient');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            req.flash('error', '세션이 만료되었습니다. 다시 로그인해주세요.');
            return res.redirect('/login');
        }
        
        const page = parseInt(req.query.page) || 1;
        const limit = parseInt(req.query.limit) || 10;
        const offset = (page - 1) * limit;
        
        const guild = await discordClient.guilds.fetch(serverId).catch(() => null);
        if (!guild) {
            req.flash('error', '봇이 서버에 접근할 수 없습니다. 다시 로그인해주세요.');
            return res.redirect('/login');
        }
        
        const serverDbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        db = getDb(serverDbPath);
        
        const totalLogs = await db.get("SELECT COUNT(*) as count FROM Logs");
        
        const logs = await db.all(`
            SELECT 
                logId, 
                timestamp, 
                userId, 
                content, 
                ip, 
                email,
                userDetails
            FROM Logs 
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
        `, [limit, offset]);
        
        const enhancedLogs = await Promise.all(
            logs.map(async (log) => {
                const userInfo = await fetchUserInfo(log.userId, discordClient);
                return {
                    ...log,
                    userInfo
                };
            })
        );
        
        const totalPages = Math.ceil(totalLogs.count / limit);
        
        res.render('logs', {
            logs: enhancedLogs,
            pagination: {
                currentPage: page,
                totalPages: totalPages,
                limit: limit
            },
            serverInfo: {
                serverId: serverId,
                name: guild.name || req.session.serverName || '서버 정보',
                iconURL: guild.iconURL({ dynamic: true }) || null
            },
            csrfToken: req.csrfToken()
        });
    } catch (error) {
        console.error('로그 조회 오류:', error);
        req.flash('error', '로그를 불러오는 중 오류가 발생했습니다.');
        res.redirect('/setting');
    } finally {
        if (db) {
            try {
                await db.close();
            } catch (err) {
                console.error('데이터베이스 연결 종료 오류:', err);
            }
        }
    }
};

/**
 * 서버 통계 정보 조회
 */
exports.getServerStats = async (req, res) => {
    let db = null;
    
    try {
        const config = req.app.get('config');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            return res.json({ success: false, message: '세션이 만료되었습니다.' });
        }
        
        const serverDbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        db = getDb(serverDbPath);
        
        const authCount = await db.get("SELECT COUNT(*) as count FROM Users");
        
        await db.close();
        
        return res.json({
            success: true,
            authCount: authCount ? authCount.count : 0
        });
    } catch (error) {
        console.error('서버 통계 정보 조회 오류:', error);
        
        if (db) {
            try {
                await db.close();
            } catch (err) {
                console.error('데이터베이스 연결 종료 오류:', err);
            }
        }
        
        return res.json({ success: false, message: '서버 정보를 불러오는 중 오류가 발생했습니다.' });
    }
};

// V1.4.2