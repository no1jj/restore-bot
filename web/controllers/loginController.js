const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const util = require('util');
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
 * 로그인 페이지 렌더링
 */
exports.renderLoginPage = (req, res) => {
    if (req.session.loggedIn) {
        return res.redirect('/setting');
    }
    res.render('login', { 
        csrfToken: req.csrfToken(),
        error: null
    });
};

/**
 * 로그인 처리 로직
 */
exports.processLogin = async (req, res) => {
    const { username, password } = req.body;
    let db = null;
    
    try {
        const config = req.app.get('config');
        db = getDb(config.DBPath);
        
        const row = await db.get("SELECT * FROM WebPanel WHERE id = ?", [username]);
        
        if (!row) {
            return res.render('login', { 
                error: '아이디 또는 비밀번호가 올바르지 않습니다.',
                csrfToken: req.csrfToken()
            });
        }
        
        let isValidPassword = false;
        
        const oldHashedPassword = require('crypto')
            .createHash('sha256')
            .update(password + row.salt)
            .digest('hex');
            
        if (oldHashedPassword === row.password) {
            isValidPassword = true;
            
            const hashedPassword = await bcrypt.hash(password, 10);
            await db.run("UPDATE WebPanel SET password = ?, salt = ? WHERE id = ?", 
                [hashedPassword, '', username]);
        } 
        else if (row.password.startsWith('$2')) {
            isValidPassword = await bcrypt.compare(password, row.password);
        }
        
        if (!isValidPassword) {
            return res.render('login', { 
                error: '아이디 또는 비밀번호가 올바르지 않습니다.',
                csrfToken: req.csrfToken()
            });
        }
        
        req.session.loggedIn = true;
        req.session.serverId = row.serverId;
        req.session.userId = row.id;
        
        req.flash('success', '로그인 성공! 환영합니다.');
        res.redirect('/setting');
    } catch (error) {
        console.error('로그인 오류:', error);
        res.status(500).render('login', { 
            error: '로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
            csrfToken: req.csrfToken()
        });
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
 * 로그아웃 처리
 */
exports.processLogout = (req, res) => {
    req.session.destroy((err) => {
        if (err) {
            console.error('로그아웃 오류:', err);
            req.flash('error', '로그아웃 중 오류가 발생했습니다.');
        }
        res.redirect('/');
    });
}; 