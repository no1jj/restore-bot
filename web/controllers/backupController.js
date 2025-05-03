const path = require('path');
const fs = require('fs');
const { promisify } = require('util');
const sqlite3 = require('sqlite3').verbose();
const { exec } = require('child_process');
const execAsync = promisify(exec);
const mkdir = promisify(fs.mkdir);
const writeFile = promisify(fs.writeFile);
const readFile = promisify(fs.readFile);

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
 * 백업 페이지 렌더링
 */
exports.renderBackupPage = async (req, res) => {
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
        
        const backupsDir = path.join(config.DBFolderPath, 'backups');
        const backups = await getServerBackups(backupsDir, serverId);
        
        res.render('backup', {
            serverInfo: {
                name: guild.name,
                id: guild.id,
                iconURL: guild.iconURL({ dynamic: true }) || null
            },
            backups: backups,
            csrfToken: req.csrfToken()
        });
        
    } catch (error) {
        console.error('백업 페이지 렌더링 오류:', error);
        req.flash('error', '백업 정보를 불러오는 중 오류가 발생했습니다.');
        res.redirect('/');
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
 * 서버 백업 실행
 */
exports.createBackup = async (req, res) => {
    try {
        res.setHeader('Content-Type', 'application/json');
        
        const config = req.app.get('config');
        const discordClient = req.app.get('discordClient');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            return res.status(401).json({ success: false, message: '세션이 만료되었습니다. 다시 로그인해주세요.' });
        }
        
        req.socket.setTimeout(600000);
        
        const guild = await discordClient.guilds.fetch(serverId).catch((error) => {
            console.error('서버 페치 오류:', error);
            return null;
        });
        
        if (!guild) {
            return res.status(404).json({ success: false, message: '봇이 서버에 접근할 수 없습니다.' });
        }
        
        const now = new Date();
        const timestamp = now.toISOString().replace(/[:.-]/g, '').replace('T', '').substring(0, 14);
        
        const backupDir = path.join(config.DBFolderPath, `backups/${serverId}_${timestamp}`);
        
        try {
            fs.mkdirSync(backupDir, { recursive: true });
        } catch (error) {
            console.error('백업 폴더 생성 오류:', error);
            return res.status(500).json({ success: false, message: '백업 폴더를 생성할 수 없습니다.' });
        }
        
        const configPath = path.join(backupDir, 'config.json');
        const backupConfig = {
            guild_id: serverId,
            backup_dir: backupDir,
            config_path: path.resolve(process.cwd(), 'config.json'),
            creator: req.session.username || (req.session.user ? req.session.user.username : 'SYSTEM'),
            creator_id: req.session.userId || (req.session.user ? req.session.user.id : 'SYSTEM')
        };
        
        try {
            fs.writeFileSync(configPath, JSON.stringify(backupConfig, null, 2));
        } catch (error) {
            console.error('백업 설정 파일 생성 오류:', error);
            try {
                fs.rmSync(backupDir, { recursive: true, force: true });
            } catch (e) {}
            return res.status(500).json({ success: false, message: '백업 설정 파일을 생성할 수 없습니다.' });
        }
        
        const scriptPath = path.join(process.cwd(), 'web', 'scripts', 'run_backup.js');
        
        if (!fs.existsSync(scriptPath)) {
            try {
                fs.rmSync(backupDir, { recursive: true, force: true });
            } catch (e) {}
            return res.status(500).json({ success: false, message: '백업 스크립트를 찾을 수 없습니다.' });
        }
        
        const execOptions = { 
            timeout: 600000, 
            maxBuffer: 1024 * 1024 * 10,
            killSignal: 'SIGTERM'
        };
        
        let execResult;
        try {
            console.log(`백업 스크립트 실행: ${scriptPath} ${configPath}`);
            execResult = await execAsync(`node "${scriptPath}" "${configPath}"`, execOptions);
            console.log('백업 스크립트 실행 완료');
        } catch (error) {
            console.error('백업 스크립트 실행 오류:', error);
            console.error('오류 메시지:', error.message);
            console.error('오류 스택:', error.stack);
            
            if (error.stderr) {
                console.error('스크립트 오류 출력:', error.stderr);
            }
            
            try {
                fs.rmSync(backupDir, { recursive: true, force: true });
            } catch (e) {}
            
            if (error.killed && error.signal === 'SIGTERM') {
                return res.status(504).json({ 
                    success: false, 
                    message: '백업 스크립트 실행 시간이 초과되었습니다. 서버 크기가 커서 시간이 오래 걸릴 수 있습니다.' 
                });
            }
            
            return res.status(500).json({ 
                success: false, 
                message: `백업 스크립트 실행 중 오류가 발생했습니다: ${error.message}` 
            });
        }
        
        if (execResult.stderr && execResult.stderr.trim() !== '') {
            console.error('백업 스크립트 오류:', execResult.stderr);
        }
        
        if (execResult.stdout) {
            console.log('백업 스크립트 출력:', execResult.stdout);
        }
        
        const resultPath = path.join(backupDir, 'backup.json');
        
        if (!fs.existsSync(resultPath)) {
            try {
                fs.rmSync(backupDir, { recursive: true, force: true });
            } catch (e) {}
            return res.status(500).json({ success: false, message: '백업 파일을 생성할 수 없습니다.' });
        }
        
        let resultData;
        try {
            const resultContent = fs.readFileSync(resultPath, 'utf-8');
            resultData = JSON.parse(resultContent);
        } catch (error) {
            console.error('백업 결과 파일 읽기 오류:', error);
            
            try {
                fs.rmSync(backupDir, { recursive: true, force: true });
            } catch (e) {}
            
            return res.status(500).json({ 
                success: false, 
                message: '백업 결과 파일을 읽을 수 없습니다: ' + (error.message || '알 수 없는 오류')
            });
        }
        
        if (!resultData.roles_data || !resultData.channels_data) {
            console.error('백업 데이터가 유효하지 않습니다:', resultData);
            
            try {
                fs.rmSync(backupDir, { recursive: true, force: true });
            } catch (e) {}
            
            return res.status(500).json({ success: false, message: '백업 데이터가 유효하지 않습니다.' });
        }
        
        return res.status(200).json({ 
            success: true, 
            message: '백업이 성공적으로 생성되었습니다.', 
            backupPath: path.basename(backupDir) 
        });
    } catch (error) {
        console.error('백업 생성 중 처리되지 않은 오류:', error);
        
        if (!res.headersSent) {
            return res.status(500).json({ 
                success: false, 
                message: `백업 생성 중 오류가 발생했습니다: ${error.message || '알 수 없는 오류'}` 
            });
        }
    }
};

/**
 * 백업 목록 조회
 */
exports.getBackupList = async (req, res) => {
    try {
        const config = req.app.get('config');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            return res.json({ success: false, message: '세션이 만료되었습니다.' });
        }
        
        const backupsDir = path.join(config.DBFolderPath, 'backups');
        const backups = await getServerBackups(backupsDir, serverId);
        
        return res.json({ success: true, backups });
        
    } catch (error) {
        console.error('백업 목록 조회 오류:', error);
        return res.json({ success: false, message: '백업 목록을 불러오는 중 오류가 발생했습니다.' });
    }
};

/**
 * 백업 상세 정보 조회
 */
exports.getBackupDetails = async (req, res) => {
    try {
        const backupPath = req.params.path;
        
        if (!backupPath) {
            return res.json({ success: false, message: '백업 경로가 지정되지 않았습니다.' });
        }
        
        if (!backupPath.match(/^\d+_.*$/)) {
            return res.json({ success: false, message: '유효하지 않은 백업 경로입니다.' });
        }
        
        const config = req.app.get('config');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            return res.json({ success: false, message: '세션이 만료되었습니다.' });
        }
        
        if (!backupPath.startsWith(serverId + '_')) {
            return res.json({ success: false, message: '해당 백업에 접근할 권한이 없습니다.' });
        }
        
        const backupDir = path.join(config.DBFolderPath, 'backups', backupPath);
        const backupJsonPath = path.join(backupDir, 'backup.json');
        
        if (!fs.existsSync(backupJsonPath)) {
            return res.json({ success: false, message: '백업 파일을 찾을 수 없습니다.' });
        }
        
        const backupData = JSON.parse(await readFile(backupJsonPath, 'utf8'));
        
        const details = {
            backupInfo: backupData.backup_info,
            serverInfo: backupData.server_info,
            stats: {
                roles: backupData.roles_data.length,
                categories: backupData.channels_data.filter(c => isCategory(c)).length,
                channels: backupData.channels_data.filter(c => !isCategory(c)).length,
                emojis: backupData.emojis_data.length,
                stickers: backupData.stickers_data.length,
                bans: Array.isArray(backupData.banned_users) ? backupData.banned_users.length : 0
            },
            path: backupPath
        };
        
        return res.json({ success: true, details });
        
    } catch (error) {
        console.error('백업 상세 정보 조회 오류:', error);
        return res.json({ success: false, message: '백업 정보를 불러오는 중 오류가 발생했습니다.' });
    }
};

/**
 * 백업 삭제
 */
exports.deleteBackup = async (req, res) => {
    try {
        const { backupPath } = req.body;
        
        if (!backupPath) {
            return res.json({ success: false, message: '백업 경로가 지정되지 않았습니다.' });
        }
        
        if (!backupPath.match(/^\d+_.*$/)) {
            return res.json({ success: false, message: '유효하지 않은 백업 경로입니다.' });
        }
        
        const config = req.app.get('config');
        const serverId = req.session.serverId;
        
        if (!serverId) {
            return res.json({ success: false, message: '세션이 만료되었습니다.' });
        }
        
        if (!backupPath.startsWith(serverId + '_')) {
            return res.json({ success: false, message: '해당 백업에 접근할 권한이 없습니다.' });
        }
        
        const backupDir = path.join(config.DBFolderPath, 'backups', backupPath);
        
        if (!fs.existsSync(backupDir)) {
            return res.json({ success: false, message: '백업 디렉토리를 찾을 수 없습니다.' });
        }
        
        fs.rmSync(backupDir, { recursive: true, force: true });
        
        return res.json({ success: true, message: '백업이 성공적으로 삭제되었습니다.' });
        
    } catch (error) {
        console.error('백업 삭제 오류:', error);
        return res.json({ success: false, message: '백업 삭제 중 오류가 발생했습니다: ' + error.message });
    }
};

/**
 * 서버 백업 목록 조회
 */
async function getServerBackups(backupsDir, serverId) {
    if (!fs.existsSync(backupsDir)) {
        console.log(`백업 디렉토리가 존재하지 않습니다: ${backupsDir}`);
        return [];
    }
    
    let allBackups = [];
    
    try {
        // 디렉토리 내용 조회
        allBackups = fs.readdirSync(backupsDir)
            .filter(name => name.startsWith(serverId + '_'))
            .filter(name => {
                try {
                    const fullPath = path.join(backupsDir, name);
                    return fs.existsSync(fullPath) && fs.statSync(fullPath).isDirectory();
                } catch (err) {
                    console.error(`디렉토리 확인 오류 (${name}):`, err);
                    return false;
                }
            });
    } catch (error) {
        console.error(`백업 디렉토리 조회 오류:`, error);
        return [];
    }
    
    if (allBackups.length === 0) {
        console.log(`${serverId} 서버의 백업을 찾을 수 없습니다.`);
        return [];
    }
    
    const backupList = [];
    
    for (const backupName of allBackups) {
        const backupDir = path.join(backupsDir, backupName);
        const backupJsonPath = path.join(backupDir, 'backup.json');
        
        if (!fs.existsSync(backupJsonPath)) {
            console.log(`백업 JSON 파일이 없습니다: ${backupJsonPath}`);
            continue;
        }
        
        try {
            const fileContent = fs.readFileSync(backupJsonPath, 'utf8');
            if (!fileContent || fileContent.trim() === '') {
                console.error(`백업 파일이 비어 있습니다: ${backupJsonPath}`);
                continue;
            }
            
            const backupData = JSON.parse(fileContent);
            
            if (!backupData.backup_info) {
                console.error(`백업 정보가 누락되었습니다: ${backupJsonPath}`);
                continue;
            }
            
            let timestamp = backupData.backup_info.timestamp || '알 수 없는 날짜';
            try {
                if (timestamp && timestamp !== '알 수 없는 날짜') {
                    const date = new Date(timestamp);
                    if (!isNaN(date)) {
                        timestamp = date.toLocaleString('ko-KR', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: false
                        });
                    }
                }
            } catch (err) {
                console.error(`타임스탬프 변환 오류: ${err.message}`);
            }
            
            const creator = backupData.backup_info.creator || '알 수 없는 생성자';
            
            const stats = {
                roles: 0,
                categories: 0,
                channels: 0,
                emojis: 0,
                stickers: 0,
                bans: 0
            };
            
            if (Array.isArray(backupData.roles_data)) {
                stats.roles = backupData.roles_data.length;
            }
            
            if (Array.isArray(backupData.channels_data)) {
                stats.categories = backupData.channels_data.filter(c => isCategory(c)).length;
                stats.channels = backupData.channels_data.filter(c => !isCategory(c)).length;
            }
            
            if (Array.isArray(backupData.emojis_data)) {
                stats.emojis = backupData.emojis_data.length;
            }
            
            if (Array.isArray(backupData.stickers_data)) {
                stats.stickers = backupData.stickers_data.length;
            }
            
            if (Array.isArray(backupData.banned_users)) {
                stats.bans = backupData.banned_users.length;
            }
            
            backupList.push({
                name: backupName,
                timestamp,
                creator,
                stats,
                path: backupName
            });
        } catch (error) {
            console.error(`백업 ${backupName} 정보 파싱 오류:`, error);
            continue;
        }
    }
    
    backupList.sort((a, b) => {
        try {
            const dateA = new Date(a.timestamp);
            const dateB = new Date(b.timestamp);
            
            if (isNaN(dateA.getTime()) || isNaN(dateB.getTime())) {
                const numA = parseInt(a.name.split('_')[1], 10);
                const numB = parseInt(b.name.split('_')[1], 10);
                return numB - numA;
            }
            
            return dateB - dateA;
        } catch (error) {
            return 0;
        }
    });
    
    return backupList;
}

/**
 * 채널이 카테고리인지 확인
 */
function isCategory(channel) {
    if (!channel || typeof channel !== 'object') {
        return false;
    }
    
    const channelType = channel.type;
    
    if (channelType === undefined || channelType === null) {
        return false;
    }
    
    if (typeof channelType === 'number') {
        return channelType === 4;
    }
    
    if (typeof channelType === 'string') {
        return channelType === '4' || channelType === 'category';
    }
    
    return false;
}

// V1.4