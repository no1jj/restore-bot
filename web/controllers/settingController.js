const path = require('path');
const sqlite3 = require('sqlite3').verbose();

/**
 * 설정 페이지 렌더링
 */
exports.renderSettingPage = (req, res) => {
    try {
        const config = req.app.get('config');
        const serverId = req.session.serverId;
        const serverDbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        
        const db = new sqlite3.Database(serverDbPath);
        
        db.serialize(() => {
            db.get("SELECT * FROM Info", [], (err, serverInfo) => {
                if (err) {
                    console.error('서버 정보 조회 오류:', err);
                    return res.status(500).send('서버 정보를 불러오는 중 오류가 발생했습니다.');
                }
                
                db.get("SELECT * FROM Settings", [], (err, settings) => {
                    db.close();
                    
                    if (err) {
                        console.error('설정 정보 조회 오류:', err);
                        return res.status(500).send('설정 정보를 불러오는 중 오류가 발생했습니다.');
                    }
                    
                    const formattedSettings = {
                        loggingIp: settings.loggingIp === 1,
                        loggingMail: settings.loggingMail === 1,
                        webhookUrl: settings.webhookUrl,
                        roleId: settings.roleId,
                        useCaptcha: settings.useCaptcha === 1,
                        blockVpn: settings.blockVpn === 1,
                        loggingChannelId: settings.loggingChannelId
                    };
                    
                    res.render('setting_panel', {
                        serverInfo: serverInfo,
                        settings: formattedSettings,
                        query: req.query
                    });
                });
            });
        });
    } catch (error) {
        console.error('설정 페이지 렌더링 오류:', error);
        res.status(500).send('서버 오류가 발생했습니다.');
    }
};

/**
 * 설정 업데이트
 */
exports.updateSettings = (req, res) => {
    try {
        const config = req.app.get('config');
        const serverId = req.session.serverId;
        const serverDbPath = path.join(config.DBFolderPath, `${serverId}.db`);
        
        const {
            loggingIp,
            loggingMail,
            webhookUrl,
            roleId,
            useCaptcha,
            blockVpn,
            loggingChannelId
        } = req.body;
        
        const db = new sqlite3.Database(serverDbPath);
        
        const settings = {
            loggingIp: loggingIp ? 1 : 0,
            loggingMail: loggingMail ? 1 : 0,
            webhookUrl: webhookUrl || '',
            roleId: roleId || '0',
            useCaptcha: useCaptcha ? 1 : 0,
            blockVpn: blockVpn ? 1 : 0,
            loggingChannelId: loggingChannelId || '0'
        };
        
        db.run(`
            UPDATE Settings SET 
            loggingIp = ?, 
            loggingMail = ?, 
            webhookUrl = ?, 
            roleId = ?, 
            useCaptcha = ?, 
            blockVpn = ?,
            loggingChannelId = ?
        `, [
            settings.loggingIp,
            settings.loggingMail,
            settings.webhookUrl,
            settings.roleId,
            settings.useCaptcha,
            settings.blockVpn,
            settings.loggingChannelId
        ], function(err) {
            db.close();
            
            if (err) {
                console.error('설정 업데이트 오류:', err);
                return res.status(500).send('설정을 저장하는 중 오류가 발생했습니다.');
            }
            
            res.redirect('/setting?success=true');
        });
    } catch (error) {
        console.error('설정 업데이트 오류:', error);
        res.status(500).send('서버 오류가 발생했습니다.');
    }
}; 