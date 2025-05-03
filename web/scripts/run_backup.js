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
    }).replace(/\. /g, '-').replace(/\.$/g, '').replace(/:/g, ':');
    
    console.log(`백업 데이터 생성 중: ${guild ? guild.id : 'undefined'}`);
    
    if (!guild) {
        throw new Error('유효하지 않은 서버 객체: undefined');
    }
    
    const serverName = config.server_name || guild.name || 'Unknown Server';
    const creatorId = config.creator_id || 'SYSTEM';
    const creatorName = creatorInfo || 'SYSTEM';
    const formattedCreator = creatorId !== 'SYSTEM' ? `${creatorName} (ID: ${creatorId})` : creatorName;
    
    const backupData = {
        backup_info: {
            timestamp: timestamp,
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
        if (guild.iconURL && typeof guild.iconURL === 'function') {
            const iconUrl = guild.iconURL({ format: 'png', size: 1024 });
            if (iconUrl) {
                const iconPath = path.join(backupDir, "icon.png");
                await downloadFile(iconUrl, iconPath);
            }
        }

        if (guild.bannerURL && typeof guild.bannerURL === 'function') {
            const bannerUrl = guild.bannerURL({ format: 'png', size: 1024 });
            if (bannerUrl) {
                const bannerPath = path.join(backupDir, "banner.png");
                await downloadFile(bannerUrl, bannerPath);
            }
        }
    } catch (error) {
        console.error(`서버 에셋 백업 실패: ${error.message}`);
    }
}

async function downloadFile(url, filePath) {
    let retries = 3;
    let delay = 1000;
    
    while (retries > 0) {
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
            
            await writeFile(filePath, response.data);
            return;
        } catch (error) {
            retries--;
            
            if (retries === 0) {
                console.error(`파일 다운로드 실패 (${url}): ${error.message}`);
                throw error;
            }
            
            console.warn(`파일 다운로드 재시도 중 (${url}): ${error.message}`);
            await new Promise(resolve => setTimeout(resolve, delay));
            delay *= 2;
        }
    }
}

function getChannelData(channel) {
    const channelOverwrites = [];
    
    channel.permissionOverwrites.cache.forEach((permissions, targetId) => {
        const target = channel.guild.roles.cache.get(targetId) || 
                      channel.guild.members.cache.get(targetId);
        
        if (target) {
            let allowValue = 0;
            let denyValue = 0;
            
            if (permissions.allow) {
                if (typeof permissions.allow.bitfield === 'bigint') {
                    allowValue = Number(permissions.allow.bitfield);
                    if (isNaN(allowValue) || !isFinite(allowValue)) {
                        allowValue = permissions.allow.bitfield.toString();
                    }
                } else {
                    allowValue = permissions.allow.bitfield;
                }
            }
            
            if (permissions.deny) {
                if (typeof permissions.deny.bitfield === 'bigint') {
                    denyValue = Number(permissions.deny.bitfield);
                    if (isNaN(denyValue) || !isFinite(denyValue)) {
                        denyValue = permissions.deny.bitfield.toString();
                    }
                } else {
                    denyValue = permissions.deny.bitfield;
                }
            }
            
            channelOverwrites.push({
                name: target.name || target.displayName || "알 수 없음",
                allow: allowValue,
                deny: denyValue
            });
        }
    });
    
    return {
        name: channel.name,
        type: channel.type,
        position: channel.position,
        nsfw: channel.nsfw || false,
        slowmode_delay: channel.rateLimitPerUser || null,
        category: channel.parent ? channel.parent.name : null,
        overwrites: channelOverwrites
    };
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
    if (!guild || !guild.roles) {
        console.warn('역할 백업 실패: 유효하지 않은 인자');
        return;
    }
    
    console.log(`역할 백업 함수 시작`);
    
    try {
        if (!guild.roles.cache || guild.roles.cache.size === 0) {
            console.log('역할 캐시가 비어 있어 역할 목록을 다시 가져옵니다...');
            await guild.roles.fetch();
            console.log(`역할 다시 가져온 후 캐시된 역할 수: ${guild.roles.cache.size}`);
        }
        
        if (!guild.roles.cache || guild.roles.cache.size === 0) {
            console.warn('역할 백업 실패: 역할을 가져올 수 없습니다.');
            return;
        }
        
        console.log(`역할 백업 함수: 역할 캐시 크기 = ${guild.roles.cache.size}`);
        
        const roleEntries = Array.from(guild.roles.cache.entries());
        console.log(`처리할 역할 수: ${roleEntries.length}`);
        
        for (const [roleId, role] of roleEntries) {
            if (!role) {
                console.warn(`ID ${roleId}의 역할이 유효하지 않음, 건너뜁니다.`);
                continue;
            }
            
            try {
                console.log(`역할 처리 중: ${role.name} (${role.id})`);
                
                let permissionValue;
                try {
                    if (role.permissions && role.permissions.bitfield !== undefined) {
                        if (typeof role.permissions.bitfield === 'bigint') {
                            permissionValue = Number(role.permissions.bitfield);
                            if (isNaN(permissionValue) || !isFinite(permissionValue)) {
                                permissionValue = role.permissions.bitfield.toString();
                            }
                        } else {
                            permissionValue = role.permissions.bitfield;
                        }
                        console.log(`역할 ${role.name}의 권한 값: ${permissionValue} (원본 타입: ${typeof role.permissions.bitfield})`);
                    } else {
                        console.warn(`역할 ${role.name}에 권한 정보가 없습니다.`);
                        permissionValue = 0;
                    }
                } catch (err) {
                    console.error(`역할 ${role.name}의 권한 변환 중 오류: ${err.message}`);
                    permissionValue = 0;
                }
                
                const roleData = {
                    id: role.id,
                    name: role.name,
                    permissions: permissionValue,
                    colour: role.color || 0,
                    color: role.color || 0,
                    hoist: role.hoist || false,
                    mentionable: role.mentionable || false,
                    position: role.position || 0
                };
                
                backupData.roles_data.push(roleData);
                console.log(`역할이 성공적으로 추가됨: ${role.name}`);
            } catch (roleError) {
                console.error(`개별 역할 처리 중 오류(${role?.name || '알 수 없음'}): ${roleError.message}`);
            }
        }
        
        console.log(`역할 백업 완료: ${backupData.roles_data.length}개 역할 처리됨`);
        
        if (backupData.roles_data.length === 0) {
            console.warn('백업된 역할이 없습니다. 최소한 @everyone 역할은 추가합니다.');
            backupData.roles_data.push({
                id: guild.id,
                name: '@everyone',
                permissions: 0,
                colour: 0,
                color: 0,
                hoist: false,
                mentionable: false,
                position: 0
            });
        }
    } catch (error) {
        console.error(`역할 백업 실패: ${error.message}`);
        console.error(error.stack);
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
                    id: ban.user.id,
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
        const emojis = await guild.emojis.fetch();
        
        if (!emojis || emojis.size === 0) {
            console.log('백업할 이모지가 없습니다.');
            backupData.emojis_data = [];
            return;
        }
        
        const emojisDir = path.join(backupDir, "emojis");
        await mkdir(emojisDir, { recursive: true });
        
        for (const [id, emoji] of emojis) {
            if (!emoji || !emoji.url) continue;
            
            const emojiPath = path.join(emojisDir, `${emoji.id}.png`);
            
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
            } catch (error) {
                console.error(`이모지 백업 실패: ${emoji.name} - ${error.message}`);
            }
        }
    } catch (error) {
        console.error(`이모지 백업 실패: ${error.message}`);
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
            console.log(`스티커 데이터 가져오기 실패: ${error.message}`);
            return null;
        });
        
        if (!stickers || stickers.size === 0) {
            console.log('백업할 스티커가 없습니다.');
            backupData.stickers_data = [];
            return;
        }
        
        const stickersDir = path.join(backupDir, "stickers");
        await mkdir(stickersDir, { recursive: true });
        
        for (const [id, sticker] of stickers) {
            if (!sticker || !sticker.url) continue;
            
            const stickerPath = path.join(stickersDir, `${sticker.id}.png`);
            
            try {
                await downloadFile(sticker.url, stickerPath);
                
                let formatType = "PNG";
                try {
                    if (sticker.format) {
                        if (typeof sticker.format === 'object') {
                            formatType = sticker.format.name || sticker.format.value || "PNG";
                        } else {
                            formatType = sticker.format;
                        }
                    }
                } catch (e) {
                    console.error(`스티커 포맷 타입 추출 오류 (${sticker.name}): ${e.message}`);
                }
                
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
            } catch (error) {
                console.error(`스티커 백업 실패: ${sticker.name} - ${error.message}`);
            }
        }
    } catch (error) {
        console.error(`스티커 백업 실패: ${error.message}`);
        backupData.stickers_data = [];
    }
}

async function backupChannels(guild, backupData) {
    if (!guild || !guild.channels || !backupData) {
        console.warn('채널 백업 실패: 유효하지 않은 인자');
        return;
    }
    
    if (!guild.channels.cache || guild.channels.cache.size === 0) {
        console.log('백업할 채널이 없습니다.');
        return;
    }
    
    try {
        const systemChannels = [
            guild.rulesChannel, 
            guild.publicUpdatesChannel, 
            guild.systemChannel
        ].filter(channel => channel !== null && channel !== undefined);
        
        const systemChannelIds = systemChannels.map(ch => ch ? ch.id : null).filter(id => id !== null);
        
        let categoryCount = 0;
        let channelCount = 0;
        
        const categoryChannels = guild.channels.cache.filter(ch => ch && ch.type === 4);
        if (categoryChannels.size === 0) {
            console.log('백업할 카테고리가 없습니다.');
        } else {
            for (const [id, channel] of categoryChannels) {
                if (!channel || systemChannelIds.includes(channel.id)) continue;
                
                try {
                    const channelOverwrites = [];
                    
                    if (channel.permissionOverwrites && channel.permissionOverwrites.cache) {
                        channel.permissionOverwrites.cache.forEach((permissions, targetId) => {
                            if (!permissions) return;
                            
                            const target = guild.roles.cache.get(targetId) || 
                                        guild.members.cache.get(targetId);
                            
                            if (target) {
                                let allowValue = 0;
                                let denyValue = 0;
                                
                                if (permissions.allow) {
                                    if (typeof permissions.allow.bitfield === 'bigint') {
                                        allowValue = Number(permissions.allow.bitfield);
                                        if (isNaN(allowValue) || !isFinite(allowValue)) {
                                            allowValue = permissions.allow.bitfield.toString();
                                        }
                                    } else {
                                        allowValue = permissions.allow.bitfield;
                                    }
                                }
                                
                                if (permissions.deny) {
                                    if (typeof permissions.deny.bitfield === 'bigint') {
                                        denyValue = Number(permissions.deny.bitfield);
                                        if (isNaN(denyValue) || !isFinite(denyValue)) {
                                            denyValue = permissions.deny.bitfield.toString();
                                        }
                                    } else {
                                        denyValue = permissions.deny.bitfield;
                                    }
                                }
                                
                                channelOverwrites.push({
                                    id: targetId,
                                    type: target.constructor.name === 'Role' ? 'role' : 'member',
                                    name: target.name || target.displayName || "알 수 없음",
                                    allow: allowValue,
                                    deny: denyValue
                                });
                            }
                        });
                    }
                    
                    const channelData = {
                        id: channel.id,
                        name: channel.name,
                        type: 4,
                        position: channel.position,
                        permission_overwrites: channelOverwrites,
                        channels: channel.children && channel.children.cache ? 
                                  channel.children.cache.map(ch => ch.id) : []
                    };
                    
                    backupData.channels_data.push(channelData);
                    categoryCount++;
                } catch (error) {
                    console.error(`카테고리 백업 실패: ${channel.name} - ${error.message}`);
                }
            }
        }
        
        const normalChannels = guild.channels.cache.filter(ch => ch && ch.type !== 4);
        if (normalChannels.size === 0) {
            console.log('백업할 일반 채널이 없습니다.');
        } else {
            for (const [id, channel] of normalChannels) {
                if (!channel || systemChannelIds.includes(channel.id)) continue;
                
                try {
                    const channelOverwrites = [];
                    
                    if (channel.permissionOverwrites && channel.permissionOverwrites.cache) {
                        channel.permissionOverwrites.cache.forEach((permissions, targetId) => {
                            if (!permissions) return;
                            
                            const target = guild.roles.cache.get(targetId) || 
                                        guild.members.cache.get(targetId);
                            
                            if (target) {
                                let allowValue = 0;
                                let denyValue = 0;
                                
                                if (permissions.allow) {
                                    if (typeof permissions.allow.bitfield === 'bigint') {
                                        allowValue = Number(permissions.allow.bitfield);
                                        if (isNaN(allowValue) || !isFinite(allowValue)) {
                                            allowValue = permissions.allow.bitfield.toString();
                                        }
                                    } else {
                                        allowValue = permissions.allow.bitfield;
                                    }
                                }
                                
                                if (permissions.deny) {
                                    if (typeof permissions.deny.bitfield === 'bigint') {
                                        denyValue = Number(permissions.deny.bitfield);
                                        if (isNaN(denyValue) || !isFinite(denyValue)) {
                                            denyValue = permissions.deny.bitfield.toString();
                                        }
                                    } else {
                                        denyValue = permissions.deny.bitfield;
                                    }
                                }
                                
                                channelOverwrites.push({
                                    id: targetId,
                                    type: target.constructor.name === 'Role' ? 'role' : 'member',
                                    name: target.name || target.displayName || "알 수 없음",
                                    allow: allowValue,
                                    deny: denyValue
                                });
                            }
                        });
                    }
                    
                    let channelType = channel.type;
                    
                    const channelData = {
                        id: channel.id,
                        name: channel.name,
                        type: channelType,
                        position: channel.position,
                        permission_overwrites: channelOverwrites,
                        parent_id: channel.parentId || null,
                        category: channel.parent ? channel.parent.name : null
                    };
                    
                    if (channel.isTextBased && channel.isTextBased()) {
                        channelData.nsfw = channel.nsfw || false;
                        channelData.topic = channel.topic || null;
                        channelData.slowmode_delay = channel.rateLimitPerUser || 0;
                        channelData.default_auto_archive_duration = 1440;
                    } 
                    else if (channel.type === 2) { 
                        channelData.bitrate = channel.bitrate || 64000;
                        channelData.user_limit = channel.userLimit || 0;
                        channelData.rtc_region = channel.rtcRegion || null;
                    }
                    else if (channel.type === 13) { 
                        channelData.topic = channel.topic || null;
                        channelData.user_limit = channel.userLimit || 0;
                        channelData.rtc_region = channel.rtcRegion || null;
                    }
                    
                    backupData.channels_data.push(channelData);
                    channelCount++;
                } catch (error) {
                    console.error(`채널 백업 실패: ${channel.name || id} - ${error.message}`);
                }
            }
        }
        
        console.log(`채널 백업 결과: ${categoryCount}개 카테고리, ${channelCount}개 일반 채널`);
    } catch (error) {
        console.error(`채널 백업 실패: ${error.message}`);
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
    if (!backupData || !backupData.channels_data || !Array.isArray(backupData.channels_data)) {
        console.error('유효하지 않은 백업 데이터 구조입니다.');
        return;
    }
    
    try {
        const sortedChannels = backupData.channels_data.sort((a, b) => {
            if (!a || !b) return 0;
            
            const aIsCategory = isCategory(a);
            const bIsCategory = isCategory(b);
            
            if (aIsCategory && !bIsCategory) return -1;
            if (!aIsCategory && bIsCategory) return 1;
            
            const aPosition = typeof a.position === 'number' ? a.position : 0;
            const bPosition = typeof b.position === 'number' ? b.position : 0;
            
            return aPosition - bPosition;
        });
        
        backupData.channels_data = sortedChannels;
        
        const categoryChannels = sortedChannels.filter(channel => isCategory(channel));
        
        for (const category of categoryChannels) {
            if (category && 'channels' in category && Array.isArray(category.channels)) {
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

// V1.4.1