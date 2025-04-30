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
        
        const db = new sqlite3.Database(dbPath);
        
        // sqlite3에서는 pragma를 직접 실행해야 함
        db.run("PRAGMA journal_mode = WAL");
        
        // 기존 함수를 Promise 기반으로 래핑
        db.prepare = function(sql) {
            const statement = {
                get: function(params, callback) {
                    if (typeof params === 'function') {
                        callback = params;
                        params = [];
                    }
                    db.get(sql, params, callback);
                    return this;
                },
                run: function(params, callback) {
                    if (typeof params === 'function') {
                        callback = params;
                        params = [];
                    }
                    db.run(sql, params, callback);
                    return this;
                },
                all: function(params, callback) {
                    if (typeof params === 'function') {
                        callback = params;
                        params = [];
                    }
                    db.all(sql, params, callback);
                    return this;
                }
            };
            return statement;
        };
        
        return db;
    } catch (error) {
        console.error(`데이터베이스 연결 실패: ${error}`);
        return null;
    }
}

/**
 * 서버 존재 여부 확인
 * @param {string} serverId - 서버 ID
 * @returns {Promise<boolean>} 존재 여부
 */
exports.checkServerExists = (serverId) => {
    return new Promise((resolve) => {
        try {
            const conn = loadDB(serverId);
            if (!conn) {
                return resolve(false);
            }
            
            conn.get("SELECT COUNT(*) as count FROM Settings", [], (err, row) => {
                if (err) {
                    console.error(`서버 존재 확인 쿼리 실패: ${err}`);
                    conn.close();
                    return resolve(false);
                }
                
                conn.close();
                return resolve(!err && row && row.count > 0);
            });
        } catch (error) {
            console.error(`서버 존재 확인 실패: ${error}`);
            resolve(false);
        }
    });
}

/**
 * 역할 ID 가져오기
 * @param {string} serverId - 서버 ID
 * @returns {Promise<string|null>} 역할 ID 또는 null
 */
exports.getRoleId = (serverId) => {
    return new Promise((resolve) => {
        try {
            const conn = loadDB(serverId);
            if (!conn) {
                return resolve(null);
            }
            
            conn.get("SELECT roleId FROM Settings", [], (err, row) => {
                if (err) {
                    console.error(`역할 ID 가져오기 쿼리 실패: ${err}`);
                    conn.close();
                    return resolve(null);
                }
                
                conn.close();
                return resolve(row && row.roleId !== undefined ? row.roleId : null);
            });
        } catch (error) {
            console.error(`역할 ID 가져오기 실패: ${error}`);
            resolve(null);
        }
    });
};

/**
 * 웹훅 URL 가져오기
 * @param {string} serverId - 서버 ID
 * @returns {Promise<string|null>} 웹훅 URL 또는 null
 */
exports.getWebhookUrl = (serverId) => {
    return new Promise((resolve) => {
        try {
            const conn = loadDB(serverId);
            if (!conn) {
                return resolve(null);
            }
            
            conn.get("SELECT webhookUrl FROM Settings", [], (err, row) => {
                if (err) {
                    console.error(`웹훅 URL 가져오기 쿼리 실패: ${err}`);
                    conn.close();
                    return resolve(null);
                }
                
                conn.close();
                return resolve(row && row.webhookUrl ? row.webhookUrl : null);
            });
        } catch (error) {
            console.error(`웹훅 URL 가져오기 실패: ${error}`);
            resolve(null);
        }
    });
};

/**
 * IP 로깅 설정 확인
 * @param {string} serverId - 서버 ID
 * @returns {Promise<boolean>} 로깅 여부
 */
exports.checkLoggingIp = (serverId) => {
    return new Promise((resolve) => {
        try {
            const conn = loadDB(serverId);
            if (!conn) {
                return resolve(false);
            }
            
            conn.get("SELECT loggingIp FROM Settings", [], (err, row) => {
                if (err) {
                    console.error(`IP 로깅 설정 확인 쿼리 실패: ${err}`);
                    conn.close();
                    return resolve(false);
                }
                
                conn.close();
                return resolve(!err && row && row.loggingIp !== undefined ? row.loggingIp === 1 : false);
            });
        } catch (error) {
            console.error(`IP 로깅 설정 확인 실패: ${error}`);
            resolve(false);
        }
    });
};

/**
 * 이메일 로깅 설정 확인
 * @param {string} serverId - 서버 ID
 * @returns {Promise<boolean>} 로깅 여부
 */
exports.checkLoggingMail = (serverId) => {
    return new Promise((resolve) => {
        try {
            const conn = loadDB(serverId);
            if (!conn) {
                return resolve(false);
            }
            
            conn.get("SELECT loggingMail FROM Settings", [], (err, row) => {
                if (err) {
                    console.error(`이메일 로깅 설정 확인 쿼리 실패: ${err}`);
                    conn.close();
                    return resolve(false);
                }
                
                conn.close();
                return resolve(!err && row && row.loggingMail !== undefined ? row.loggingMail === 1 : false);
            });
        } catch (error) {
            console.error(`이메일 로깅 설정 확인 실패: ${error}`);
            resolve(false);
        }
    });
};

/**
 * VPN 차단 설정 확인
 * @param {string} serverId - 서버 ID
 * @returns {Promise<boolean>} 차단 여부
 */
exports.checkBlockVpn = (serverId) => {
    return new Promise((resolve) => {
        try {
            const conn = loadDB(serverId);
            if (!conn) {
                return resolve(false);
            }
            
            conn.get("SELECT blockVpn FROM Settings", [], (err, row) => {
                if (err) {
                    console.error(`VPN 차단 설정 확인 쿼리 실패: ${err}`);
                    conn.close();
                    return resolve(false);
                }
                
                conn.close();
                return resolve(!err && row && row.blockVpn !== undefined ? row.blockVpn === 1 : false);
            });
        } catch (error) {
            console.error(`VPN 차단 설정 확인 실패: ${error}`);
            resolve(false);
        }
    });
};

/**
 * 캡챠 사용 설정 확인
 * @param {string} serverId - 서버 ID
 * @returns {Promise<boolean>} 사용 여부
 */
exports.checkUsingCaptcha = (serverId) => {
    return new Promise((resolve) => {
        try {
            const conn = loadDB(serverId);
            if (!conn) {
                return resolve(false);
            }
            
            conn.get("SELECT useCaptcha FROM Settings", [], (err, row) => {
                if (err) {
                    console.error(`캡챠 사용 설정 확인 쿼리 실패: ${err}`);
                    conn.close();
                    return resolve(false);
                }
                
                conn.close();
                return resolve(!err && row && row.useCaptcha !== undefined ? row.useCaptcha === 1 : false);
            });
        } catch (error) {
            console.error(`캡챠 사용 설정 확인 실패: ${error}`);
            resolve(false);
        }
    });
};

/**
 * 사용자 존재 여부 확인
 * @param {string} guildId - 서버 ID
 * @param {string} userId - 사용자 ID
 * @returns {Promise<boolean>} 존재 여부
 */
exports.checkUserExists = async (guildId, userId) => {
    try {
        const conn = loadDB(guildId);
        if (!conn) {
            return false;
        }
        
        return new Promise((resolve) => {
            conn.get("SELECT COUNT(*) as count FROM Users WHERE userId = ?", [userId], (err, row) => {
                conn.close();
                if (err) {
                    console.error(`사용자 존재 확인 실패: ${err}`);
                    resolve(false);
                } else {
                    resolve(row && row.count > 0);
                }
            });
        });
    } catch (error) {
        console.error(`사용자 존재 확인 실패: ${error}`);
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
        
        conn.run(
            "INSERT INTO Users (userId, refreshToken, email, serviceToken, ip) VALUES (?, ?, ?, ?, ?)", 
            [userId, refToken, email, serviceToken, ip], 
            (err) => {
                if (err) {
                    console.error(`사용자 추가 실패: ${err}`);
                }
                conn.close();
            }
        );
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
        
        conn.run(
            "UPDATE Users SET refreshToken = ?, email = ?, ip = ? WHERE userId = ?", 
            [refreshToken, email, ip, userId], 
            (err) => {
                if (err) {
                    console.error(`사용자 정보 업데이트 실패: ${err}`);
                }
                conn.close();
            }
        );
    } catch (error) {
        console.error(`사용자 정보 업데이트 실패: ${error}`);
    }
};

/**
 * 화이트리스트 확인
 * @param {string} userId - 사용자 ID
 * @param {string} ip - IP 주소
 * @param {string} email - 이메일
 * @returns {Promise<boolean>} 화이트리스트 여부
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
 * @returns {Promise<boolean>} 블랙리스트 여부
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

exports.loadDB = loadDB; 