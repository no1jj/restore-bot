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
 * 고유 링크 설정 페이지 렌더링
 */
exports.renderLinkPage = async (req, res) => {
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
        
        res.render('link_page', {
            serverInfo: {
                name: guild.name,
                id: guild.id,
                iconURL: guild.iconURL({ dynamic: true }) || null
            },
            linkInfo: linkInfo || null,
            fullUrl: linkInfo ? `${req.protocol}://${req.get('host')}/j/${linkInfo.customLink}` : null,
            csrfToken: req.csrfToken()
        });
    } catch (error) {
        console.error('고유 링크 페이지 렌더링 오류:', error);
        if (db) {
            try {
                await db.close();
            } catch (err) {
                console.error('데이터베이스 연결 종료 오류:', err);
            }
        }
        req.flash('error', '페이지를 불러오는 중 오류가 발생했습니다.');
        res.redirect('/setting');
    }
};

// V1.5