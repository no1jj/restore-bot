const path = require('path');
const sqlite3 = require('sqlite3').verbose();
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
        
        const settingsQuery = await db.get("SELECT loggingIp, loggingMail FROM Settings");
        const loggingIp = settingsQuery && settingsQuery.loggingIp === 1;
        const loggingMail = settingsQuery && settingsQuery.loggingMail === 1;
        
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
                
                const filteredLog = {
                    ...log,
                    ip: loggingIp ? log.ip : null,
                    email: loggingMail ? log.email : null,
                    userInfo
                };
                
                return filteredLog;
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

// V1.5.2