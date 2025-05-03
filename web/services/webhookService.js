const { WebhookClient } = require('discord.js');
const dbService = require('./dbService');
const ipService = require('./ipService');
const path = require('path');

/**
 * 웹훅 로그 전송
 * @param {string} guildId - 서버 ID
 * @param {string} title - 로그 제목
 * @param {string} description - 로그 설명
 * @param {number} color - 로그 색상 (16진수)
 * @param {Array} fields - 필드 배열
 * @param {object} userInfo - 사용자 정보
 * @returns {boolean} 전송 성공 여부
 */
exports.sendWebhookLog = async (guildId, title, description, color, fields = [], userInfo = null) => {
    try {
        const config = require(path.join(__dirname, '../../config.json'));
        const webhookUrl = await dbService.getWebhookUrl(guildId);
        const ownerWebhookUrl = config.ownerLogWebhook;
        
        if (!webhookUrl && !ownerWebhookUrl) return false;
        
        const embed = {
            title: title,
            description: description,
            color: color,
            timestamp: new Date(),
            fields: fields
        };
        
        if (title.includes('인증 성공') || title.includes('인증 완료')) {
            title = '인증 로그';
            embed.title = title;
        }
        
        if (description && description.includes('블랙리스트')) {
            title = '인증 차단 로그';
            embed.title = title;
        }
        
        let serverName = '알 수 없음';
        try {
            const conn = dbService.loadDB(guildId);
            if (conn) {
                await new Promise((resolve) => {
                    conn.get("SELECT name FROM Info", [], (err, row) => {
                        if (!err && row && row.name) {
                            serverName = row.name;
                        }
                        conn.close();
                        resolve();
                    });
                });
            }
        } catch (err) {
            console.error('서버 이름 조회 실패:', err);
        }
        
        if (userInfo) {
            const isWhitelisted = await dbService.checkIsWhitelisted(userInfo.userId, userInfo.ip, userInfo.email);
            const isBlacklisted = description && description.includes('블랙리스트');
            
            if (title.includes('인증 로그') && userInfo.userId && !isBlacklisted) {
                try {
                    const client = require('../app').get('discordClient');
                    const user = await client.users.fetch(userInfo.userId);
                    if (user) {
                        const dmEmbed = {
                            title: "🎉 인증 완료!",
                            description: `**${serverName}** 서버의 인증이 완료되었습니다.`,
                            color: 0x57F287,
                            timestamp: new Date()
                        };
                        
                        await user.send({ embeds: [dmEmbed] }).catch(err => {
                            console.error('DM 전송 실패:', err);
                        });
                    }
                } catch (dmError) {
                    console.error('DM 전송 중 오류:', dmError);
                }
            }
            
            if (webhookUrl) {
                const serverEmbed = { ...embed };
                serverEmbed.fields = [];
                
                serverEmbed.description = `
🔔 **${title}**
${description ? `${description}\n` : ''}`;

                if (title.includes('인증 로그') || title.includes('인증 차단') || isBlacklisted) {
                    serverEmbed.description += `\n👤 **사용자 정보**
  • 👥 ${userInfo.userId ? `<@${userInfo.userId}>` : '알 수 없음'}
  • 📝 \`${userInfo.globalName || userInfo.username || '알 수 없음'} (${userInfo.username || '알 수 없음'})\`
  • 🆔 \`${userInfo.userId || '알 수 없음'}\``;
                    
                    const loggingMail = await dbService.checkLoggingMail(guildId);
                    if (isBlacklisted) {
                        serverEmbed.description += `\n  • 📧 \`${userInfo.email || '이메일 없음'}\``;
                    } else if (!isWhitelisted && loggingMail && userInfo.email) {
                        serverEmbed.description += `\n  • 📧 \`${userInfo.email}\``;
                    }
                    
                    if (!isWhitelisted) {
                        const loggingIp = await dbService.checkLoggingIp(guildId);
                        if (loggingIp && userInfo.ip) {
                            serverEmbed.description += `\n\n🌐 **IP 정보**
  • 🔍 \`${userInfo.ip}\``;
                            
                            if (userInfo.ip !== '알 수 없음') {
                                const ipInfo = await ipService.getIpInfo(userInfo.ip);
                                if (ipInfo) {
                                    serverEmbed.description += `
  • 🗺️ \`${ipInfo.country}, ${ipInfo.region}\`
  • 🔌 \`${ipInfo.isp}\``;
                                }
                            }
                        }
                        
                        serverEmbed.description += `\n\n📱 **기기 정보**
  • 🖥️ \`${userInfo.os || '알 수 없음'}\`
  • 🌏 \`${userInfo.browser || '알 수 없음'}\``;
                    } else {
                        serverEmbed.description += `\n\n✅ **화이트리스트 상태**
  • ✨ \`등록된 사용자\``;
                    }
                    
                    if (isBlacklisted) {
                        serverEmbed.description += `\n\n🚫 **블랙리스트 상태**
  • ⛔ \`차단된 사용자\``;
                    }
                } else {
                    serverEmbed.description += `\n👤 **사용자 정보**
  • 👥 ${userInfo.userId ? `<@${userInfo.userId}>` : '알 수 없음'}
  • 📝 \`${userInfo.globalName || userInfo.username || '알 수 없음'} (${userInfo.username || '알 수 없음'})\`
  • 🆔 \`${userInfo.userId || '알 수 없음'}\``;
                    
                    const loggingMail = await dbService.checkLoggingMail(guildId);
                    if (!isWhitelisted && loggingMail && userInfo.email) {
                        serverEmbed.description += `\n  • 📧 \`${userInfo.email}\``;
                    }
                    
                    if (!isWhitelisted) {
                        const loggingIp = await dbService.checkLoggingIp(guildId);
                        if (loggingIp && userInfo.ip) {
                            serverEmbed.description += `\n\n🌐 **IP 정보**
  • 🔍 \`${userInfo.ip}\``;
                        }
                        
                        serverEmbed.description += `\n\n📱 **기기 정보**
  • 🖥️ \`${userInfo.os || '알 수 없음'}\`
  • 🌏 \`${userInfo.browser || '알 수 없음'}\``;
                    } else {
                        serverEmbed.description += `\n\n✅ **화이트리스트 상태**
  • ✨ \`등록된 사용자\``;
                    }
                }
                
                try {
                    const webhookClient = new WebhookClient({ url: webhookUrl });
                    await webhookClient.send({ embeds: [serverEmbed] });
                } catch (error) {
                    console.error('웹훅 전송 실패:', error);
                }
            }
            
            if (ownerWebhookUrl) {
                const ownerEmbed = { ...embed };
                ownerEmbed.fields = []; 
                
                ownerEmbed.description = `
🔔 **${title}**
${description ? `${description}\n` : ''}
🏢 **서버 정보**
  • 🆔 \`${guildId}(${serverName})\`

👤 **사용자 정보**
  • 👥 ${userInfo.userId ? `<@${userInfo.userId}>` : '알 수 없음'}
  • 📝 \`${userInfo.globalName || userInfo.username || '알 수 없음'} (${userInfo.username || '알 수 없음'})\`
  • 🆔 \`${userInfo.userId || '알 수 없음'}\`
  • 📧 \`${userInfo.email || '이메일 없음'}\``;

                if (userInfo.ip && userInfo.ip !== '알 수 없음') {
                    ownerEmbed.description += `\n\n🌐 **IP 정보**
  • 🔍 \`${userInfo.ip}\``;
                
                    const ipInfo = await ipService.getIpInfo(userInfo.ip);
                    if (ipInfo) {
                        const { country, region, isp } = ipInfo;
                        ownerEmbed.description += `
  • 🗺️ \`${country}, ${region}\`
  • 🔌 \`${isp}\``;
                    }
                } else {
                    ownerEmbed.description += `\n\n🌐 **IP 정보**
  • 🔍 \`알 수 없음\``;
                }
                
                ownerEmbed.description += `\n\n📱 **기기 정보**
  • 🖥️ \`${userInfo.os || '알 수 없음'}\`
  • 🌏 \`${userInfo.browser || '알 수 없음'}\``;
                
                if (isWhitelisted) {
                    ownerEmbed.description += `\n\n✅ **화이트리스트 상태**
  • ✨ \`등록된 사용자\``;
                }
                
                if (isBlacklisted) {
                    ownerEmbed.description += `\n\n🚫 **블랙리스트 상태**
  • ⛔ \`차단된 사용자\``;
                }
                
                try {
                    const ownerWebhookClient = new WebhookClient({ url: ownerWebhookUrl });
                    await ownerWebhookClient.send({ embeds: [ownerEmbed] });
                } catch (error) {
                    console.error('관리자 웹훅 전송 실패:', error);
                }
            }
        } else {
            if (webhookUrl) {
                const serverEmbed = { ...embed };
                
                serverEmbed.description = `
🔔 **${title}**
${description ? `${description}` : ''}`;
                
                serverEmbed.fields = [];
                
                try {
                    const webhookClient = new WebhookClient({ url: webhookUrl });
                    await webhookClient.send({ embeds: [serverEmbed] });
                } catch (error) {
                    console.error('웹훅 전송 실패:', error);
                }
            }
            
            if (ownerWebhookUrl) {
                const ownerEmbed = { ...embed };
                
                ownerEmbed.description = `
🔔 **${title}**
${description ? `${description}\n` : ''}
🏢 **서버 정보**
  • 🆔 \`${guildId}(${serverName})\``;
                
                ownerEmbed.fields = []; 
                
                try {
                    const ownerWebhookClient = new WebhookClient({ url: ownerWebhookUrl });
                    await ownerWebhookClient.send({ embeds: [ownerEmbed] });
                } catch (error) {
                    console.error('관리자 웹훅 전송 실패:', error);
                }
            }
        }
        
        return true;
    } catch (error) {
        console.error('웹훅 로그 전송 오류:', error);
        return false;
    }
}; 

// V1.3.2