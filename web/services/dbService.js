const path = require('path');
const sqlite3 = require('sqlite3').verbose();

/**
 * 서버별 데이터베이스 연결
 * @param {string} serverId - 서버 ID
 * @returns {object|null} 데이터베이스 연결 객체 또는 null
 */
function loadDB(serverId) {
    try {
        const config = require('../../config.json');
        const dbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        
        const db = require('better-sqlite3')(dbPath);
        
        db.pragma('journal_mode = WAL');
        
        return db;
    } catch (error) {
        console.error(`데이터베이스 연결 실패: ${error}`);
        return null;
    }
}

/**
 * 서버 존재 여부 확인
 * @param {string} serverId - 서버 ID
 * @returns {boolean} 존재 여부
 */
exports.checkServerExists = (serverId) => {
    try {
        const conn = loadDB(serverId);
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
};

/**
 * 역할 ID 가져오기
 * @param {string} serverId - 서버 ID
 * @returns {string|null} 역할 ID 또는 null
 */
exports.getRoleId = (serverId) => {
    try {
        const conn = loadDB(serverId);
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
};

/**
 * 웹훅 URL 가져오기
 * @param {string} serverId - 서버 ID
 * @returns {string|null} 웹훅 URL 또는 null
 */
exports.getWebhookUrl = (serverId) => {
    try {
        const conn = loadDB(serverId);
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
};

/**
 * IP 로깅 설정 확인
 * @param {string} serverId - 서버 ID
 * @returns {boolean} 로깅 여부
 */
exports.checkLoggingIp = (serverId) => {
    try {
        const conn = loadDB(serverId);
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
};

/**
 * 이메일 로깅 설정 확인
 * @param {string} serverId - 서버 ID
 * @returns {boolean} 로깅 여부
 */
exports.checkLoggingMail = (serverId) => {
    try {
        const conn = loadDB(serverId);
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
};

/**
 * VPN 차단 설정 확인
 * @param {string} serverId - 서버 ID
 * @returns {boolean} 차단 여부
 */
exports.checkBlockVpn = (serverId) => {
    try {
        const conn = loadDB(serverId);
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
};

/**
 * 캡챠 사용 설정 확인
 * @param {string} serverId - 서버 ID
 * @returns {boolean} 사용 여부
 */
exports.checkUsingCaptcha = (serverId) => {
    try {
        const conn = loadDB(serverId);
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
};

/**
 * 사용자 존재 여부 확인
 * @param {string} guildId - 서버 ID
 * @param {string} userId - 사용자 ID
 * @returns {boolean} 존재 여부
 */
exports.checkUserExists = async (guildId, userId) => {
    try {
        const conn = loadDB(guildId);
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
};

/**
 * 사용자 추가
 * @param {string} guildId - 서버 ID
 * @param {string} userId - 사용자 ID
 * @param {string} refToken - 리프레시 토큰
 * @param {string} email - 이메일
 * @param {string} serviceToken - 서비스 토큰
 * @param {string} ip - IP 주소
 */
exports.addUser = (guildId, userId, refToken, email, serviceToken, ip) => {
    try {
        const conn = loadDB(guildId);
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
};

/**
 * 사용자 정보 업데이트
 * @param {string} guildId - 서버 ID
 * @param {string} userId - 사용자 ID
 * @param {string} refreshToken - 리프레시 토큰
 * @param {string} email - 이메일
 * @param {string} ip - IP 주소
 */
exports.updateUser = (guildId, userId, refreshToken, email, ip) => {
    try {
        const conn = loadDB(guildId);
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
};

/**
 * 화이트리스트 확인
 * @param {string} userId - 사용자 ID
 * @param {string} ip - IP 주소
 * @param {string} email - 이메일
 * @returns {boolean} 화이트리스트 여부
 */
exports.checkIsWhitelisted = async (userId, ip, email) => {
    try {
        const config = require('../../config.json');
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
};

/**
 * 블랙리스트 확인
 * @param {string} userId - 사용자 ID
 * @param {string} ip - IP 주소
 * @param {string} email - 이메일
 * @returns {boolean} 블랙리스트 여부
 */
exports.checkIsBlacklisted = async (userId, ip, email) => {
    try {
        const config = require('../../config.json');
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
};

// 모듈 내보내기
exports.loadDB = loadDB; 