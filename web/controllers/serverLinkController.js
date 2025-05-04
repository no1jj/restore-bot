const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const discordService = require('../services/discordService');
const { promisify } = require('util');

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

exports.handleCustomLink = async (req, res) => {
    const customLink = req.params.customLink;
    let db = null;
    
    try {
        const config = req.app.get('config');
        const discordClient = req.app.get('discordClient');
        
        const dbPath = config.DBPath; 
        db = getDb(dbPath);
        
        const linkInfo = await db.get(
            "SELECT serverId FROM ServerCustomLinks WHERE customLink = ?",
            [customLink]
        );
        
        if (!linkInfo) {
            if (db) await db.close();
            db = null;
            return res.status(404).render("error", { 
                message: "존재하지 않는 링크입니다.",
                settings: { nodeEnv: config.nodeEnv },
                error: null
            });
        }
        
        const serverId = linkInfo.serverId;
        
        await db.run(
            "UPDATE ServerCustomLinks SET lastUsed = datetime('now'), visitCount = visitCount + 1 WHERE customLink = ?",
            [customLink]
        );
        
        if (db) {
            await db.close();
            db = null;
        }

        const guild = await discordClient.guilds.fetch(serverId).catch(() => null);
        if (!guild) {
            return res.status(500).render("error", { 
                message: "서버 정보를 가져올 수 없습니다.",
                settings: { nodeEnv: config.nodeEnv },
                error: null
            });
        }
        
        let memberCount = guild.memberCount || 0;
        let onlineCount = 0;
        
        try {
            const members = await guild.members.fetch();
            onlineCount = members.filter(member => 
                member.presence?.status === 'online' || 
                member.presence?.status === 'idle' || 
                member.presence?.status === 'dnd'
            ).size;
        } catch (error) {
            console.error('멤버 목록 조회 오류:', error);
            onlineCount = Math.floor(memberCount * 0.3);
        }
        
        let isInServer = false;
        let userId = null;
        
        if (req.session.user) {
            userId = req.session.user.id;
            try {
                await guild.members.fetch(userId);
                isInServer = true;
            } catch (error) {
                isInServer = false;
            }
        }
        
        const authUrl = discordService.getAuthUrl(serverId, config);
        
        return res.render("auth", {
            serverInfo: {
                id: serverId,
                name: guild.name,
                iconURL: guild.iconURL({ dynamic: true }),
                memberCount: memberCount,
                onlineCount: onlineCount
            },
            isInServer: isInServer,
            authUrl: authUrl
        });
    } catch (error) {
        console.error('고유 링크 처리 오류:', error);
        if (db) {
            try {
                await db.close();
            } catch (closeError) {
                console.error('DB 연결 종료 오류:', closeError);
            }
            db = null; 
        }
        const config = req.app.get('config');
        return res.status(500).render("error", { 
            message: "서버 오류가 발생했습니다.",
            settings: { nodeEnv: config.nodeEnv },
            error: error
        });
    }
};

exports.setupCustomLink = async (req, res) => {
    const { customLink } = req.body;
    const serverId = req.session.serverId;
    let db = null;
    
    try {
        if (!customLink || customLink.length < 3 || customLink.length > 30) {
            return res.json({ success: false, message: "링크는 3~30자 사이여야 합니다." });
        }
    
        if (!/^[a-zA-Z0-9\-_]+$/.test(customLink)) {
            return res.json({ success: false, message: "링크는 영문, 숫자, 하이픈, 언더스코어만 사용 가능합니다." });
        }
        
        const config = req.app.get('config');
        const dbPath = config.DBPath;
        db = getDb(dbPath);
        
        const existingLink = await db.get(
            "SELECT serverId FROM ServerCustomLinks WHERE customLink = ? AND serverId != ?",
            [customLink, serverId]
        );
        
        if (existingLink) {
            if (db) await db.close();
            db = null;
            return res.json({ success: false, message: "이미 사용 중인 링크입니다." });
        }
        
        const myLink = await db.get(
            "SELECT customLink FROM ServerCustomLinks WHERE serverId = ?",
            [serverId]
        );
        
        if (myLink) {
            await db.run(
                "UPDATE ServerCustomLinks SET customLink = ?, updatedAt = datetime('now') WHERE serverId = ?",
                [customLink, serverId]
            );
        } else {
            await db.run(
                "INSERT INTO ServerCustomLinks (serverId, customLink, createdAt, visitCount) VALUES (?, ?, datetime('now'), 0)",
                [serverId, customLink]
            );
        }
        
        if (db) {
            await db.close();
            db = null;
        }
        
        const fullUrl = `${req.protocol}://${req.get('host')}/j/${customLink}`;
        
        return res.json({
            success: true,
            message: "고유 링크가 설정되었습니다.",
            linkInfo: {
                customLink: customLink,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                visitCount: myLink ? undefined : 0
            },
            fullUrl: fullUrl
        });
    } catch (error) {
        console.error('고유 링크 설정 오류:', error);
        if (db) {
            try {
                await db.close();
            } catch (closeError) {
                console.error('DB 연결 종료 오류:', closeError);
            }
            db = null; 
        }
        return res.json({ success: false, message: "링크 설정 중 오류가 발생했습니다." });
    }
};

exports.getServerCustomLink = async (req, res) => {
    const serverId = req.session.serverId;
    let db = null;
    
    try {
        const config = req.app.get('config');
        const dbPath = config.DBPath;
        db = getDb(dbPath);
        
        const linkInfo = await db.get(
            "SELECT customLink, createdAt, lastUsed, visitCount FROM ServerCustomLinks WHERE serverId = ?",
            [serverId]
        );
        
        if (db) {
            await db.close();
            db = null;
        }
        
        return res.json({
            success: true,
            linkInfo: linkInfo || null,
            fullUrl: linkInfo ? `${req.protocol}://${req.get('host')}/j/${linkInfo.customLink}` : null
        });
    } catch (error) {
        console.error('링크 정보 조회 오류:', error);
        if (db) {
            try {
                await db.close();
            } catch (closeError) {
                console.error('DB 연결 종료 오류:', closeError);
            }
            db = null; 
        }
        return res.json({ success: false, message: "링크 정보 조회 중 오류가 발생했습니다." });
    }
};

// V1.5