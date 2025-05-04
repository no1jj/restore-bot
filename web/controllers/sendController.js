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
 * 인증 메시지 페이지 렌더링
 */
exports.renderSendPage = async (req, res) => {
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
        
        const settings = await db.get("SELECT roleId FROM Settings");
        
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
        
        res.render('send_auth', {
            serverInfo: {
                name: guild.name,
                id: guild.id,
                iconURL: guild.iconURL({ dynamic: true }) || null
            },
            settings: {
                roleId: settings ? settings.roleId : ''
            },
            channels: textChannels,
            csrfToken: req.csrfToken()
        });
    } catch (error) {
        console.error('인증 메시지 페이지 렌더링 오류:', error);
        req.flash('error', '페이지를 불러오는 중 오류가 발생했습니다.');
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

// V1.4.2 