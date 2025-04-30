const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const { promisify } = require('util');
const { ChannelType, PermissionFlagsBits } = require('discord.js');

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
            serverInfo: serverInfo,
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
        
        const newWebhook = await channel.createWebhook({
            name: 'RestoreBot',
            avatar: 'https://i.imgur.com/wSTFkRM.png',
            reason: '서버 설정에서 생성됨'
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

// V1.1