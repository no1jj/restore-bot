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
 * 서버 정보 페이지 렌더링
 */
exports.renderInfoPage = async (req, res) => {
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
            req.flash('error', '봇이 서버에 접근할 수 없습니다. 다시 로그인해주세요.');
            return res.redirect('/login');
        }
        
        const serverDbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        db = getDb(serverDbPath);
        
        const serverInfo = await db.get("SELECT * FROM Info");
        
        if (!serverInfo) {
            req.flash('error', '서버 정보를 찾을 수 없습니다.');
            return res.redirect('/login');
        }
        
        const authCount = await db.get("SELECT COUNT(*) as count FROM Users");
        
        res.render('info', {
            serverInfo: {
                name: guild.name,
                id: guild.id,
                iconURL: guild.iconURL({ dynamic: true }) || null,
                key: serverInfo.key,
                date: serverInfo.date,
                authCount: authCount ? authCount.count : 0
            },
            csrfToken: req.csrfToken()
        });
    } catch (error) {
        console.error('서버 정보 페이지 렌더링 오류:', error);
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
 * 서버 정보 업데이트
 */
exports.updateInfo = async (req, res) => {
    let db = null;
    
    try {
        const config = req.app.get('config');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            return res.json({ success: false, message: '세션이 만료되었습니다. 다시 로그인해주세요.' });
        }
        
        const serverDbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        db = getDb(serverDbPath);
        
        const { name } = req.body;
        
        if (!name || typeof name !== 'string' || name.trim().length === 0) {
            return res.json({ success: false, message: '서버 이름은 필수 항목입니다.' });
        }
        
        await db.run("UPDATE Info SET name = ?", [name.trim()]);
        
        return res.json({ 
            success: true, 
            message: '서버 정보가 성공적으로 업데이트되었습니다.'
        });
    } catch (error) {
        console.error('서버 정보 업데이트 오류:', error);
        return res.json({ success: false, message: '서버 정보 업데이트 중 오류가 발생했습니다.' });
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

// V1.5