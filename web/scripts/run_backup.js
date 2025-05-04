const fs = require('fs');
const path = require('path');
const { Client, GatewayIntentBits, PermissionsBitField } = require('discord.js');
const { exec } = require('child_process');
const https = require('https');
const http = require('http');
const { promisify } = require('util');
const axios = require('axios');

if (process.argv.length !== 3) {
    console.log("사용법: node run_backup.js <config_file>");
    process.exit(1);
}

const configPath = process.argv[2];

const mkdir = promisify(fs.mkdir);
const writeFile = promisify(fs.writeFile);
const readFile = promisify(fs.readFile);

BigInt.prototype.toJSON = function() { 
    return this.toString();
};

function safeStringify(obj) {
    try {
        return JSON.stringify(obj, null, 2);
    } catch (error) {
        console.error('JSON 직렬화 오류:', error.message);
        
        const cache = new Set();
        const safeJson = JSON.stringify(obj, (key, value) => {
            if (typeof value === 'object' && value !== null) {
                if (cache.has(value)) {
                    return '[순환 참조]';
                }
                cache.add(value);
            }
            
            if (typeof value === 'bigint') {
                return value.toString();
            }
            
            return value;
        }, 2);
        
        return safeJson;
    }
}

function safeParse(text) {
    try {
        return JSON.parse(text);
    } catch (error) {
        console.error('JSON 파싱 오류:', error.message);
        throw new Error(`JSON 파싱 오류: ${error.message}`);
    }
}

function validateBackupData(data) {
    if (!data || typeof data !== 'object') {
        throw new Error('백업 데이터가 객체가 아닙니다');
    }
    
    const requiredFields = ['backup_info', 'server_info', 'roles_data', 'channels_data'];
    for (const field of requiredFields) {
        if (!data[field]) {
            throw new Error(`백업 데이터에 필수 필드가 없습니다: ${field}`);
        }
    }
    
    const arrayFields = ['roles_data', 'channels_data', 'emojis_data', 'stickers_data', 'banned_users'];
    for (const field of arrayFields) {
        if (data[field] && !Array.isArray(data[field])) {
            data[field] = [];
        }
    }
    
    return data;
}

async function main() {
    try {
        if (!fs.existsSync(configPath)) {
            throw new Error(`설정 파일을 찾을 수 없습니다: ${configPath}`);
        }
        
        console.log(`설정 파일 경로: ${configPath}`);
        
        let config;
        let token;
        
        try {
            const configData = await readFile(configPath, 'utf8');
            console.log(`설정 파일 내용: ${configData}`);
            config = safeParse(configData);
            console.log('파싱된 설정:', {
                guild_id: config.guild_id ? config.guild_id.substring(0, 5) + '...' : undefined,
                backup_dir: config.backup_dir,
                config_path: config.config_path
            });
            
            try {
                const mainConfigPath = path.join(__dirname, '../../config.json');
                console.log(`메인 설정 파일 경로: ${mainConfigPath}`);
                
                if (fs.existsSync(mainConfigPath)) {
                    const mainConfigData = await readFile(mainConfigPath, 'utf8');
                    const mainConfig = safeParse(mainConfigData);
                    token = mainConfig.botToken;
                    console.log('메인 설정 파일 로드 성공');
                    console.log('토큰 로딩 상태:', !!token);
                } else {
                    throw new Error(`메인 설정 파일을 찾을 수 없습니다: ${mainConfigPath}`);
                }
            } catch (configError) {
                throw new Error(`메인 설정 파일 로드 실패: ${configError.message}`);
            }
            
            if (!config.guild_id || !config.backup_dir) {
                console.error('필수 설정 누락:', {
                    guild_id: !!config.guild_id, 
                    backup_dir: !!config.backup_dir
                });
                throw new Error('설정 파일에 필수 정보가 누락되었습니다.');
            }
            
            if (!token) {
                throw new Error('봇 토큰을 찾을 수 없습니다. config.json 파일에 botToken 필드가 있는지 확인하세요.');
            }
        } catch (error) {
            throw new Error(`설정 파일 파싱 오류: ${error.message}`);
        }
    
        const guildId = config.guild_id;
        const backupDir = config.backup_dir;
        
        console.log(`백업 시작: 서버 ID ${guildId}, 경로 ${backupDir}`);
        
        if (!fs.existsSync(backupDir)) {
            try {
                await mkdir(backupDir, { recursive: true });
                console.log(`백업 디렉토리 생성됨: ${backupDir}`);
            } catch (error) {
                throw new Error(`백업 디렉토리 생성 실패: ${error.message}`);
            }
        }
        
        const resultPath = path.join(backupDir, 'backup.json');
        
        const client = new Client({ 
            intents: [
                GatewayIntentBits.Guilds,
                GatewayIntentBits.GuildMembers,
                GatewayIntentBits.GuildBans,
                GatewayIntentBits.GuildEmojisAndStickers,
                GatewayIntentBits.GuildIntegrations,
                GatewayIntentBits.GuildWebhooks,
                GatewayIntentBits.GuildInvites,
                GatewayIntentBits.GuildVoiceStates,
                GatewayIntentBits.GuildMessages,
                GatewayIntentBits.GuildMessageReactions,
                GatewayIntentBits.MessageContent
            ]
        });
        
        console.log('디스코드 클라이언트 초기화 완료, 로그인 시도 중...');
        
        try {
            if (!token) {
                throw new Error('토큰이 정의되지 않았습니다. 토큰 변수 확인이 필요합니다.');
            }
            
            const loginPromise = client.login(token);
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('디스코드 로그인 타임아웃')), 30000);
            });
            
            await Promise.race([loginPromise, timeoutPromise]);
            
            console.log('디스코드 클라이언트 로그인 성공');
        } catch (loginError) {
            throw new Error(`디스코드 로그인 실패: ${loginError.message}`);
        }
        
        const guild = await client.guilds.fetch(guildId);
        
        if (!guild) {
            throw new Error(`서버를 찾을 수 없습니다: ${guildId}`);
        }
        
        console.log(`서버 백업 시작: ${guild.name} (${guildId})`);
        
        const creatorInfo = config.creator || 'SYSTEM';
        const backupData = await createServerBackup(guild, backupDir, creatorInfo, config);
        
        if (!backupData || !backupData.server_info) {
            throw new Error('백업 데이터 생성 실패: 유효하지 않은 데이터');
        }
        
        sortBackupData(backupData);
        
        const jsonData = safeStringify(backupData);
        await writeFile(resultPath, jsonData, 'utf8');
        console.log(`백업 파일 저장 완료: ${resultPath}`);
        
        const stats = {
            categories: backupData.channels_data.filter(c => isCategory(c)).length,
            channels: backupData.channels_data.filter(c => !isCategory(c)).length,
            roles: backupData.roles_data.length,
            emojis: backupData.emojis_data ? backupData.emojis_data.length : 0,
            stickers: backupData.stickers_data ? backupData.stickers_data.length : 0,
            bans: Array.isArray(backupData.banned_users) ? backupData.banned_users.length : 0
        };
        
        console.log(`백업 완료: ${JSON.stringify(stats)}`);
        client.destroy();
        
        process.exit(0);
    } catch (error) {
        console.error(`치명적 오류: ${error.message}`);
        console.error(`오류 스택: ${error.stack}`);
        
        if (configPath && fs.existsSync(configPath)) {
            try {
                const backupDir = path.dirname(configPath);
                const resultPath = path.join(backupDir, 'backup.json');
                
                const errorBackup = {
                    backup_info: {
                        timestamp: new Date().toISOString(),
                        error: error.message,
                        creator: 'SYSTEM (오류 복구)'
                    },
                    server_info: { name: '오류 발생', id: '알 수 없음' },
                    roles_data: [],
                    channels_data: [],
                    emojis_data: [],
                    stickers_data: [],
                    banned_users: []
                };
                
                fs.writeFileSync(resultPath, JSON.stringify(errorBackup, null, 2));
                console.log(`오류 백업 파일 생성됨: ${resultPath}`);
            } catch (writeError) {
                console.error('오류 백업 파일 생성 실패:', writeError.message);
            }
        }
        
        process.exit(1);
    }
}

async function createServerBackup(guild, backupDir, creatorInfo, config) {
    const now = new Date();
    const timestamp = now.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    }).replace(/\. /g, '-').replace(/\.$/g, '').replace(/-/g, '-');
    
    const pythonFormatTimestamp = timestamp.replace(/-(\d+)-(\d+)-(\d+):(\d+)$/, '-$1-$2 $3:$4');
    
    console.log(`백업 데이터 생성 중: ${guild ? guild.id : 'undefined'}`);
    
    if (!guild) {
        throw new Error('유효하지 않은 서버 객체: undefined');
    }
    
    const serverName = config.server_name || guild.name || 'Unknown Server';
    const creatorId = config.creator_id || 'SYSTEM';
    const creatorName = creatorInfo || 'SYSTEM';
    
    let formattedCreator;
    if (creatorId !== 'SYSTEM') {
        if (creatorName.includes('ID:')) {
            formattedCreator = creatorName;
        } else {
            formattedCreator = `${creatorName} (ID: ${creatorId})`;
        }
    } else {
        formattedCreator = creatorName;
    }
    
    const backupData = {
        backup_info: {
            timestamp: pythonFormatTimestamp,
            creator: formattedCreator
        },
        server_info: {
            name: serverName,
            id: guild.id,
            is_community: guild.features && Array.isArray(guild.features) ? guild.features.includes("COMMUNITY") : false
        },
        roles_data: [],
        channels_data: [],
        emojis_data: [],
        stickers_data: [],
        banned_users: []
    };
    
    let successCount = 0;
    let skipCount = 0;
    
    try {
        try {
            console.log("백업 폴더 구조 생성 중...");
            if (!fs.existsSync(backupDir)) {
                await mkdir(backupDir, { recursive: true });
                console.log(`백업 메인 디렉토리 생성됨: ${backupDir}`);
            }
            
            const emojisDir = path.join(backupDir, "emojis");
            if (!fs.existsSync(emojisDir)) {
                await mkdir(emojisDir, { recursive: true });
                console.log(`이모지 디렉토리 생성됨: ${emojisDir}`);
            }
            
            const stickersDir = path.join(backupDir, "stickers");
            if (!fs.existsSync(stickersDir)) {
                await mkdir(stickersDir, { recursive: true });
                console.log(`스티커 디렉토리 생성됨: ${stickersDir}`);
            }
            
            console.log("백업 폴더 구조 생성 완료");
        } catch (dirError) {
            console.error(`백업 폴더 구조 생성 중 오류: ${dirError.message}`);
        }
        
        await saveServerAssets(guild, backupDir);
        
        await backupSystemChannels(guild, backupData);
        
        try {
            console.log(`역할 백업 시작: 역할 목록 가져오기 시도`);
            await guild.roles.fetch();
            console.log(`역할 목록 가져오기 성공: 총 ${guild.roles.cache.size}개 역할 발견`);
            
            if (guild.roles.cache.size > 0) {
                await backupRoles(guild, backupData);
                successCount++;
                console.log(`역할 백업 성공: ${backupData.roles_data.length}개 역할`);
            } else {
                skipCount++;
                console.log("역할 백업 건너뜀: 백업할 역할이 없습니다.");
            }
        } catch (error) {
            console.error(`역할 백업 중 오류 발생: ${error.message}`);
            console.error(error.stack);
            skipCount++;
        }
        
        try {
            await backupBannedUsers(guild, backupData);
            if (backupData.banned_users.length > 0) {
                successCount++;
                console.log(`차단 사용자 백업 성공: ${backupData.banned_users.length}명`);
            } else {
                skipCount++;
                console.log("차단 사용자 백업 건너뜀: 차단된 사용자가 없습니다.");
            }
        } catch (error) {
            skipCount++;
            console.log(`차단 사용자 백업 건너뜀: ${error.message}`);
        }
        
        try {
            await backupEmojis(guild, backupDir, backupData);
            if (backupData.emojis_data.length > 0) {
                successCount++;
                console.log(`이모지 백업 성공: ${backupData.emojis_data.length}개 이모지`);
            } else {
                skipCount++;
                console.log("이모지 백업 건너뜀: 백업할 이모지가 없습니다.");
            }
        } catch (error) {
            skipCount++;
            console.log(`이모지 백업 건너뜀: ${error.message}`);
        }
        
        try {
            await backupStickers(guild, backupDir, backupData);
            if (backupData.stickers_data.length > 0) {
                successCount++;
                console.log(`스티커 백업 성공: ${backupData.stickers_data.length}개 스티커`);
            } else {
                skipCount++;
                console.log("스티커 백업 건너뜀: 백업할 스티커가 없습니다.");
            }
        } catch (error) {
            skipCount++;
            console.log(`스티커 백업 건너뜀: ${error.message}`);
        }
        
        if (guild.channels && guild.channels.cache && guild.channels.cache.size > 0) {
            await backupChannels(guild, backupData);
            if (backupData.channels_data.length > 0) {
                successCount++;
                console.log(`채널 백업 성공: ${backupData.channels_data.length}개 채널`);
            } else {
                skipCount++;
                console.log("채널 백업 건너뜀: 백업할 채널이 없습니다.");
            }
        } else {
            skipCount++;
            console.log("채널 백업 건너뜀: 백업할 채널이 없습니다.");
        }
    } catch (error) {
        console.error(`백업 생성 중 오류 발생: ${error.message}`);
    } finally {
        try {
            sortBackupData(backupData);
        } catch (error) {
            console.error(`백업 데이터 정렬 중 오류 발생: ${error.message}`);
        }
        
        try {
            const validatedData = validateBackupData(backupData);
            const jsonData = safeStringify(validatedData);
            
            await writeFile(path.join(backupDir, "backup.json"), jsonData, 'utf8');
            console.log(`백업 완료 상태: ${successCount}개 성공, ${skipCount}개 건너뜀`);
            console.log('백업 파일이 성공적으로 저장되었습니다.');
        } catch (error) {
            console.error(`백업 파일 저장 중 오류 발생: ${error.message}`);
        }
    }
    
    return backupData;
}

async function saveServerAssets(guild, backupDir) {
    if (!guild) {
        console.warn('서버 에셋 백업 실패: 유효하지 않은 서버 객체');
        return;
    }
    
    try {
        console.log(`서버 아이콘 백업 시도: 서버 ID ${guild.id}, 서버명 ${guild.name}`);
        
        const hasIcon = guild.icon !== null && guild.icon !== undefined;
        console.log(`서버 아이콘 존재 여부: ${hasIcon ? '있음' : '없음'}`);
        
        if (hasIcon) {
            const iconHash = guild.icon;
            const isAnimated = iconHash.startsWith('a_');
            const extension = isAnimated ? 'gif' : 'png';
            const directIconUrl = `https://cdn.discordapp.com/icons/${guild.id}/${iconHash}.${extension}?size=4096`;
            console.log(`직접 구성한 아이콘 URL: ${directIconUrl}`);
            
            let normalIconUrl = null;
            try {
                if (guild.iconURL && typeof guild.iconURL === 'function') {
                    normalIconUrl = guild.iconURL({ extension: extension, size: 4096 });
                    console.log(`Discord.js API를 통한 아이콘 URL: ${normalIconUrl}`);
                }
            } catch (urlError) {
                console.warn(`iconURL 함수 호출 오류 (무시하고 계속 진행): ${urlError.message}`);
            }
            
            const iconUrl = normalIconUrl || directIconUrl;
            const iconPath = path.join(backupDir, "icon." + extension);
            console.log(`최종 선택된 아이콘 URL: ${iconUrl}`);
            console.log(`아이콘 저장 경로: ${iconPath}`);
            
            try {
                await downloadFile(iconUrl, iconPath);
                console.log('서버 아이콘 백업 성공');
            } catch (downloadError) {
                console.error(`아이콘 다운로드 실패 (무시하고 계속 진행): ${downloadError.message}`);
                
                if (normalIconUrl && iconUrl === directIconUrl) {
                    console.log('대체 URL로 아이콘 다운로드 재시도...');
                    try {
                        await downloadFile(normalIconUrl, iconPath);
                        console.log('대체 URL로 서버 아이콘 백업 성공');
                    } catch (retryError) {
                        console.error(`대체 URL로 아이콘 다운로드 재시도 실패 (무시하고 계속 진행): ${retryError.message}`);
                    }
                }
            }
        } else {
            console.log('서버에 아이콘이 없습니다, 건너뜁니다');
        }
    } catch (iconError) {
        console.error(`아이콘 백업 과정 전체 오류 (무시하고 계속 진행): ${iconError.message}`);
    }

    try {
        console.log(`서버 배너 백업 시도: 서버 ID ${guild.id}`);
        
        const hasBanner = guild.banner !== null && guild.banner !== undefined;
        console.log(`서버 배너 존재 여부: ${hasBanner ? '있음' : '없음'}`);
        
        if (hasBanner) {
            const bannerHash = guild.banner;
            const isAnimated = bannerHash.startsWith('a_');
            const extension = isAnimated ? 'gif' : 'png';
            const directBannerUrl = `https://cdn.discordapp.com/banners/${guild.id}/${bannerHash}.${extension}?size=4096`;
            console.log(`직접 구성한 배너 URL: ${directBannerUrl}`);
            
            let normalBannerUrl = null;
            try {
                if (guild.bannerURL && typeof guild.bannerURL === 'function') {
                    normalBannerUrl = guild.bannerURL({ extension: extension, size: 4096 });
                    console.log(`Discord.js API를 통한 배너 URL: ${normalBannerUrl}`);
                }
            } catch (urlError) {
                console.warn(`bannerURL 함수 호출 오류 (무시하고 계속 진행): ${urlError.message}`);
            }
            
            const bannerUrl = normalBannerUrl || directBannerUrl;
            const bannerPath = path.join(backupDir, "banner." + extension);
            console.log(`최종 선택된 배너 URL: ${bannerUrl}`);
            console.log(`배너 저장 경로: ${bannerPath}`);
            
            try {
                await downloadFile(bannerUrl, bannerPath);
                console.log('서버 배너 백업 성공');
            } catch (downloadError) {
                console.error(`배너 다운로드 실패 (무시하고 계속 진행): ${downloadError.message}`);
                
                if (normalBannerUrl && bannerUrl === directBannerUrl) {
                    console.log('대체 URL로 배너 다운로드 재시도...');
                    try {
                        await downloadFile(normalBannerUrl, bannerPath);
                        console.log('대체 URL로 서버 배너 백업 성공');
                    } catch (retryError) {
                        console.error(`대체 URL로 배너 다운로드 재시도 실패 (무시하고 계속 진행): ${retryError.message}`);
                    }
                }
            }
        } else {
            console.log('서버에 배너가 없습니다, 건너뜁니다');
        }
    } catch (bannerError) {
        console.error(`배너 백업 과정 전체 오류 (무시하고 계속 진행): ${bannerError.message}`);
    }
}

async function downloadFile(url, filePath) {
    if (!url) {
        console.log('다운로드 URL이 없음, 건너뜁니다');
        return;
    }
    
    let retries = 3;
    let delay = 1000;
    
    while (retries > 0) {
        try {
            console.log(`${url} 다운로드 시도 중...`);
            
            let responseData = null;
            
            try {
                const response = await axios({
                    url,
                    method: 'GET',
                    responseType: 'arraybuffer',
                    timeout: 60000,
                    maxContentLength: 20 * 1024 * 1024,
                    validateStatus: status => status >= 200 && status < 300,
                    headers: {
                        'User-Agent': 'RestoreBot/1.0'
                    }
                });
                responseData = response.data;
                console.log(`axios로 다운로드 성공: ${url} (크기: ${responseData.length} 바이트)`);
            } catch (axiosError) {
                console.warn(`axios 다운로드 실패, 다른 방법 시도: ${axiosError.message}`);
                
                responseData = await new Promise((resolve, reject) => {
                    const httpModule = url.startsWith('https') ? https : http;
                    const request = httpModule.get(url, {
                        headers: { 'User-Agent': 'RestoreBot/1.0' },
                        timeout: 60000
                    }, (response) => {
                        if (response.statusCode < 200 || response.statusCode >= 300) {
                            reject(new Error(`HTTP 상태 코드 오류: ${response.statusCode}`));
                            return;
                        }
                        
                        const chunks = [];
                        response.on('data', (chunk) => chunks.push(chunk));
                        response.on('end', () => resolve(Buffer.concat(chunks)));
                    });
                    
                    request.on('error', reject);
                    request.on('timeout', () => {
                        request.destroy();
                        reject(new Error('요청 타임아웃'));
                    });
                    
                    request.end();
                });
                console.log(`https 모듈로 다운로드 성공: ${url} (크기: ${responseData.length} 바이트)`);
            }
            
            if (!responseData || responseData.length === 0) {
                console.warn(`다운로드한 파일이 비어 있습니다: ${url}, 건너뜁니다`);
                return;
            }
            
            try {
                const fileDir = path.dirname(filePath);
                if (!fs.existsSync(fileDir)) {
                    await mkdir(fileDir, { recursive: true });
                    console.log(`디렉토리 생성: ${fileDir}`);
                }
                
                await writeFile(filePath, responseData);
                console.log(`파일 저장 완료: ${filePath}`);
            } catch (writeError) {
                console.error(`파일 저장 오류 (무시하고 계속 진행): ${writeError.message}`);
            }
            
            return;
        } catch (error) {
            retries--;
            
            if (retries === 0) {
                console.error(`파일 다운로드 실패 (무시하고 계속 진행): ${url}, ${error.message}`);
                return;  
            }
            
            console.warn(`파일 다운로드 재시도 중 (${url}): ${error.message}, 남은 시도: ${retries}`);
            await new Promise(resolve => setTimeout(resolve, delay));
            delay *= 2;
        }
    }
}

function getChannelData(channel) {
    try {
        if (!channel) return null;
        
        const channelOverwrites = [];
        
        if (channel.permissionOverwrites && channel.permissionOverwrites.cache) {
            for (const [id, overwrite] of channel.permissionOverwrites.cache) {
                try {
                    const target = overwrite.type === 0 ? 
                        channel.guild.roles.cache.get(id) : 
                        channel.guild.members.cache.get(id);
                    
                    const name = target ? target.name : `Unknown (${id})`;
                    
                    channelOverwrites.push({
                        name: name,
                        allow: overwrite.allow.bitfield,
                        deny: overwrite.deny.bitfield
                    });
                } catch (overwriteError) {
                    console.error(`채널 덮어쓰기 데이터 처리 중 오류: ${overwriteError.message}`);
                }
            }
        }
        
        const category = channel.parent ? channel.parent.name : null;
        
        let topics = null;
        if (channel.topic) topics = channel.topic;
        
        const defaultAutoArchiveDuration = channel.defaultAutoArchiveDuration || null;
        
        const channelData = {
            id: channel.id,
            type: channel.type,
            name: channel.name,
            position: channel.position,
            parent: null,
            topic: topics,
            nsfw: channel.nsfw || false,
            rate_limit_per_user: channel.rateLimitPerUser || 0,
            default_auto_archive_duration: defaultAutoArchiveDuration,
            overwrites: channelOverwrites,
            category: category
        };
        
        return channelData;
    } catch (error) {
        console.error(`채널 데이터 생성 중 오류: ${error.message}`);
        return null;
    }
}

async function backupSystemChannels(guild, backupData) {
    if (!guild || !backupData || !backupData.server_info) {
        console.warn('시스템 채널 백업 실패: 유효하지 않은 인자');
        return;
    }
    
    let systemChannelsCount = 0;
    
    try {
        if (guild.rulesChannel) {
            backupData.server_info.rules_channel = getChannelData(guild.rulesChannel);
            systemChannelsCount++;
        } else {
            backupData.server_info.rules_channel = null;
        }
        
        if (guild.publicUpdatesChannel) {
            backupData.server_info.public_updates_channel = getChannelData(guild.publicUpdatesChannel);
            systemChannelsCount++;
        } else {
            backupData.server_info.public_updates_channel = null;
        }
        
        if (guild.systemChannel) {
            backupData.server_info.system_channel = {
                name: guild.systemChannel.name,
                type: "text",
                position: guild.systemChannel.position,
                nsfw: guild.systemChannel.nsfw || false,
                category: guild.systemChannel.parent ? guild.systemChannel.parent.name : null
            };
        } else {
            backupData.server_info.system_channel = null;
        }
    } catch (error) {
        console.error(`시스템 채널 백업 실패: ${error.message}`);
    }
}

async function backupRoles(guild, backupData) {
    if (!guild || !guild.roles || !guild.roles.cache) {
        console.warn('역할 백업 실패: 유효하지 않은 역할 캐시');
        return;
    }

    let roles = Array.from(guild.roles.cache.values());
    if (!roles || !Array.isArray(roles) || roles.length === 0) {
        console.warn('역할 백업 실패: 역할이 없습니다');
        return;
    }

    try {
        roles.sort((a, b) => b.position - a.position);
        
        for (const role of roles) {
            if (role.name === '@everyone') continue;

            try {
                const roleData = {
                    id: role.id,
                    name: role.name,
                    permissions: role.permissions.bitfield,
                    colour: role.color ? role.color.toString(16) : 0,
                    color: role.color ? role.color.toString(16) : 0,
                    hoist: role.hoist || false,
                    mentionable: role.mentionable || false,
                    position: role.position || 0
                };
                
                backupData.roles_data.push(roleData);
            } catch (roleError) {
                console.error(`역할 백업 중 오류: ${role.name} - ${roleError.message}`);
            }
        }
    } catch (error) {
        console.error(`역할 백업 전체 오류: ${error.message}`);
        throw error;
    }
}

async function backupBannedUsers(guild, backupData) {
    if (!guild || !guild.bans || !backupData) {
        console.warn('차단 사용자 백업 실패: 유효하지 않은 인자');
        backupData.banned_users = [];
        return;
    }
    
    try {
        const bans = await guild.bans.fetch();
        
        if (!bans || bans.size === 0) {
            console.log('차단된 사용자가 없습니다.');
            backupData.banned_users = [];
            return;
        }
        
        const banList = [];
        
        bans.forEach(ban => {
            if (ban && ban.user) {
                banList.push({
                    id: parseInt(ban.user.id, 10),
                    reason: ban.reason
                });
            }
        });
        
        backupData.banned_users = banList;
    } catch (error) {
        console.error(`차단 사용자 백업 실패: ${error.message}`);
        backupData.banned_users = [];
    }
}

async function backupEmojis(guild, backupDir, backupData) {
    if (!guild || !guild.emojis || !backupDir || !backupData) {
        console.warn('이모지 백업 실패: 유효하지 않은 인자');
        backupData.emojis_data = [];
        return;
    }
    
    try {
        const emojis = await guild.emojis.fetch().catch(error => {
            console.warn(`이모지 목록 가져오기 실패 (무시하고 계속 진행): ${error.message}`);
            return null;
        });
        
        if (!emojis || emojis.size === 0) {
            console.log('백업할 이모지가 없습니다.');
            backupData.emojis_data = [];
            return;
        }
        
        const emojisDir = path.join(backupDir, "emojis");
        if (!fs.existsSync(emojisDir)) {
            try {
                await mkdir(emojisDir, { recursive: true });
                console.log(`이모지 디렉토리 생성됨: ${emojisDir}`);
            } catch (mkdirError) {
                console.error(`이모지 디렉토리 생성 실패 (무시하고 계속 진행): ${mkdirError.message}`);
                backupData.emojis_data = [];
                return;
            }
        }
        
        console.log(`이모지 백업 시작: 총 ${emojis.size}개`);
        let successCount = 0;
        
        for (const [id, emoji] of emojis) {
            if (!emoji || !emoji.url) {
                console.log(`이모지 건너뜀: ID ${id} (URL 정보 없음)`);
                continue;
            }
            
            const emojiFormat = emoji.animated ? 'gif' : 'png';
            const emojiPath = path.join(emojisDir, `${emoji.id}.${emojiFormat}`);
            console.log(`이모지 다운로드 시도: ${emoji.name} (${emoji.url})`);
            
            try {
                await downloadFile(emoji.url, emojiPath);
                
                const emojiData = {
                    id: emoji.id,
                    name: emoji.name,
                    path: emojiPath,
                    url: emoji.url,
                    animated: emoji.animated,
                    managed: emoji.managed,
                    available: emoji.available,
                    roles: emoji.roles && emoji.roles.cache ? emoji.roles.cache.map(role => role.id) : []
                };
                
                backupData.emojis_data.push(emojiData);
                successCount++;
                console.log(`이모지 백업 성공: ${emoji.name}`);
            } catch (error) {
                console.error(`이모지 백업 실패 (무시하고 계속 진행): ${emoji.name} - ${error.message}`);
            }
        }
        
        console.log(`이모지 백업 완료: ${successCount}/${emojis.size}개 성공`);
    } catch (error) {
        console.error(`이모지 백업 실패 (무시하고 계속 진행): ${error.message}`);
        backupData.emojis_data = [];
    }
}

async function backupStickers(guild, backupDir, backupData) {
    if (!guild || !guild.stickers || !backupDir || !backupData) {
        console.warn('스티커 백업 실패: 유효하지 않은 인자');
        backupData.stickers_data = [];
        return;
    }
    
    try {
        const stickers = await guild.stickers.fetch().catch(error => {
            console.warn(`스티커 데이터 가져오기 실패 (무시하고 계속 진행): ${error.message}`);
            return null;
        });
        
        if (!stickers || stickers.size === 0) {
            console.log('백업할 스티커가 없습니다.');
            backupData.stickers_data = [];
            return;
        }
        
        const stickersDir = path.join(backupDir, "stickers");
        if (!fs.existsSync(stickersDir)) {
            try {
                await mkdir(stickersDir, { recursive: true });
                console.log(`스티커 디렉토리 생성됨: ${stickersDir}`);
            } catch (mkdirError) {
                console.error(`스티커 디렉토리 생성 실패 (무시하고 계속 진행): ${mkdirError.message}`);
                backupData.stickers_data = [];
                return;
            }
        }
        
        console.log(`스티커 백업 시작: 총 ${stickers.size}개`);
        let successCount = 0;
        
        for (const [id, sticker] of stickers) {
            if (!sticker || !sticker.url) {
                console.log(`스티커 건너뜀: ID ${id} (URL 정보 없음)`);
                continue;
            }
            
            let formatType = "PNG";
            let formatExtension = "png";
            try {
                if (sticker.format) {
                    if (typeof sticker.format === 'object') {
                        formatType = sticker.format.name || sticker.format.value || "PNG";
                    } else {
                        formatType = sticker.format;
                    }
                    
                    if (formatType === "LOTTIE" || formatType === 3) {
                        formatExtension = "json";
                    } else if (formatType === "GIF" || formatType === 2) {
                        formatExtension = "gif";
                    } else {
                        formatExtension = "png";
                    }
                }
            } catch (e) {
                console.warn(`스티커 포맷 타입 추출 오류 (무시하고 계속 진행): ${sticker.name} - ${e.message}`);
            }
            
            const stickerPath = path.join(stickersDir, `${sticker.id}.${formatExtension}`);
            console.log(`스티커 다운로드 시도: ${sticker.name} (${sticker.url})`);
            
            try {
                await downloadFile(sticker.url, stickerPath);
                
                const stickerData = {
                    id: sticker.id,
                    name: sticker.name,
                    description: sticker.description,
                    emoji: sticker.tags && sticker.tags.length > 0 ? sticker.tags[0] : null,
                    path: stickerPath,
                    url: sticker.url,
                    format_type: formatType,
                    available: getattr(sticker, 'available', true)
                };
                
                backupData.stickers_data.push(stickerData);
                successCount++;
                console.log(`스티커 백업 성공: ${sticker.name}`);
            } catch (error) {
                console.error(`스티커 백업 실패 (무시하고 계속 진행): ${sticker.name} - ${error.message}`);
            }
        }
        
        console.log(`스티커 백업 완료: ${successCount}/${stickers.size}개 성공`);
    } catch (error) {
        console.error(`스티커 백업 실패 (무시하고 계속 진행): ${error.message}`);
        backupData.stickers_data = [];
    }
}

async function backupChannels(guild, backupData) {
    const systemChannels = [
        guild.rulesChannel, 
        guild.publicUpdatesChannel, 
        guild.systemChannel
    ].filter(channel => channel !== null);
    
    const systemChannelIds = systemChannels.map(channel => channel ? channel.id : null);
    
    for (const [id, channel] of guild.channels.cache.filter(channel => channel.type === 4)) {
        if (systemChannelIds.includes(id)) continue;
        
        try {
            const channelOverwrites = [];
            
            channel.permissionOverwrites.cache.forEach(permission => {
                const target = permission.type === 0 
                    ? guild.roles.cache.get(permission.id) 
                    : guild.members.cache.get(permission.id);
                
                if (!target) return;
                
                const targetId = permission.id;
                const targetType = permission.type === 0 ? "role" : "member";
                
                channelOverwrites.push({
                    id: targetId,
                    type: targetType,
                    name: target.name || "Unknown",
                    allow: permission.allow.bitfield.toString(),
                    deny: permission.deny.bitfield.toString()
                });
            });
            
            const childChannelIds = guild.channels.cache
                .filter(ch => ch.parentId === channel.id)
                .map(ch => ch.id);
            
            const channelData = {
                id: channel.id,
                name: channel.name,
                type: 4,
                position: channel.position,
                permission_overwrites: channelOverwrites,
                channels: childChannelIds
            };
            
            backupData.channels_data.push(channelData);
        } catch (error) {
            console.error(`카테고리 채널 백업 오류 (${channel.name}): ${error.message}`);
        }
    }
    
    for (const [id, channel] of guild.channels.cache.filter(channel => channel.type !== 4)) {
        if (systemChannelIds.includes(id)) continue;
        
        try {
            const channelOverwrites = [];
            
            channel.permissionOverwrites.cache.forEach(permission => {
                const target = permission.type === 0 
                    ? guild.roles.cache.get(permission.id) 
                    : guild.members.cache.get(permission.id);
                
                if (!target) return;
                
                const targetId = permission.id;
                const targetType = permission.type === 0 ? "role" : "member";
                
                channelOverwrites.push({
                    id: targetId,
                    type: targetType,
                    name: target.name || "Unknown",
                    allow: permission.allow.bitfield.toString(),
                    deny: permission.deny.bitfield.toString()
                });
            });
            
            const channelData = {
                id: channel.id,
                name: channel.name,
                type: channel.type,
                position: channel.position,
                permission_overwrites: channelOverwrites,
                parent_id: channel.parentId,
                category: channel.parent ? channel.parent.name : null
            };
            
            if (channel.type === 0) {
                channelData.nsfw = channel.nsfw;
                channelData.topic = channel.topic;
                channelData.slowmode_delay = channel.rateLimitPerUser;
                channelData.default_auto_archive_duration = channel.defaultAutoArchiveDuration;
            } else if (channel.type === 2) {
                channelData.bitrate = channel.bitrate;
                channelData.user_limit = channel.userLimit;
                channelData.rtc_region = channel.rtcRegion;
            } else if (channel.type === 13) {
                channelData.topic = channel.topic;
                channelData.user_limit = channel.userLimit;
                channelData.rtc_region = channel.rtcRegion;
            }
            
            backupData.channels_data.push(channelData);
        } catch (error) {
            console.error(`채널 백업 오류 (${channel.name}): ${error.message}`);
        }
    }
}

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

function sortBackupData(backupData) {
    try {
        const sortedChannels = backupData.channels_data.sort((a, b) => {
            const aIsCategory = isCategory(a);
            const bIsCategory = isCategory(b);
            
            if (aIsCategory && !bIsCategory) return -1;
            if (!aIsCategory && bIsCategory) return 1;
            
            return (a.position || 0) - (b.position || 0);
        });
        
        backupData.channels_data = sortedChannels;
        
        const categoryChannels = sortedChannels.filter(channel => isCategory(channel));
        for (const category of categoryChannels) {
            if (category.channels && Array.isArray(category.channels)) {
                category.channels = category.channels.sort();
            }
        }
    } catch (error) {
        console.error(`백업 데이터 정렬 오류: ${error.message}`);
    }
}

function getattr(obj, key, defaultValue) {
    if (!obj) return defaultValue;
    return obj[key] === undefined ? defaultValue : obj[key];
}

main().catch(err => {
    console.error(`${err.message}`);
    process.exit(1);
}); 

//V1.5.1