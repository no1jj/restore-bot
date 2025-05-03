const axios = require('axios');
const discordService = require('../services/discordService');
const dbService = require('../services/dbService');
const webhookService = require('../services/webhookService');
const helpers = require('../utils/helpers');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

exports.handleAuthCallback = async (req, res) => {
    const method = req.method;
    const state = method === "GET" ? req.query.state : req.body.state;
    const code = method === "GET" ? req.query.code : req.body.code;
    const config = req.app.get('config');
    const client = req.app.get('discordClient');
    
    if (!state || !code) {
        return res.status(400).render("auth_error", { ErrorCode: "1", Ctx: "인증 정보가 올바르지 않습니다." });
    }
    
    try {
        const guildId = state;
        
        if (method === "POST" && req.body['h_captcha_response']) {
            const captchaResponse = req.body['h_captcha_response'];
            const tokenResult = await discordService.exchangeToken(code, config, guildId);
            
            if (!tokenResult) {
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
            }
            
            return await processAuth(guildId, code, captchaResponse, req, res, tokenResult, config, client);
        }
        
        const usingCaptcha = await dbService.checkUsingCaptcha(guildId);
        
        if (usingCaptcha) {
            return res.render("captcha_check", { 
                state: guildId, 
                actoken: code, 
                sitekey: config.hCaptchaSiteKey 
            });
        } else {
            const tokenResult = await discordService.exchangeToken(code, config, guildId);
            
            if (!tokenResult) {
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
            }
            
            return await processAuth(guildId, code, null, req, res, tokenResult, config, client);
        }
    } catch (error) {
        console.error('인증 콜백 처리 중 예외 발생:', error);
        await webhookService.sendWebhookLog(state, '인증 실패', '처리 중 예외 발생', 0xFF0000, [
            { name: '오류 내용', value: `\`${error.message || '알 수 없는 오류'}\`` }
        ]);
        return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
    }
};

async function processAuth(guildId, code, hcaptchaResponse, req, res, tokenResult, config, client) {
    try {
        if (hcaptchaResponse) {
            const hcPass = await helpers.verifyCaptcha(hcaptchaResponse, config);
            if (!hcPass) {
                await webhookService.sendWebhookLog(guildId, '인증 실패', '캡챠 인증 실패', 0xFF0000);
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
            }
        }

        let userIp = (req.headers['x-forwarded-for'] || req.socket.remoteAddress)?.split(',')[0]?.trim() || '알 수 없음';
        
        if (userIp === '::1') userIp = '127.0.0.1';
        else if (userIp.startsWith('::ffff:')) userIp = userIp.substring(7);
        
        const userAgent = req.headers['user-agent'] || '없음';
        const { OS: userOs, Browser: userBrowser } = helpers.parseUserAgent(userAgent);
        
        let isVpn = false;
        let blockVpn = false;
        
        try {
            isVpn = await helpers.checkIsVpn(userIp, config);
        } catch (error) {
            console.error('VPN 확인 실패', error);
        }
        
        if (isVpn) {
            try {
                blockVpn = await dbService.checkBlockVpn(guildId);
            } catch (error) {
                console.error('VPN 차단 여부 확인 실패', error);
            }
            
            if (blockVpn) {
                const userInfo = {
                    ip: userIp,
                    os: userOs,
                    browser: userBrowser
                };
                await webhookService.sendWebhookLog(guildId, '인증 실패', 'VPN 사용으로 인증 거부됨', 0xFF0000, [], userInfo);
                return res.status(403).render("auth_error", { ErrorCode: "2", Ctx: "VPN을 사용한 인증은 허용되지 않습니다." });
            }
        }
        
        const serverExists = await dbService.checkServerExists(guildId);
        if (!serverExists) {
            await webhookService.sendWebhookLog(guildId, '인증 실패', '서버가 존재하지 않음', 0xFF0000);
            return res.status(404).render("auth_error", { ErrorCode: "3", Ctx: "서버가 존재하지 않습니다." });
        }
        
        const roleId = await dbService.getRoleId(guildId);
        
        if (!roleId) {
            await webhookService.sendWebhookLog(guildId, '인증 실패', '역할 설정이 없음', 0xFF0000);
            return res.status(404).render("auth_error", { ErrorCode: "4", Ctx: "역할 설정이 없습니다." });
        }
        
        const roleIdStr = roleId.toString();
        
        try {
            const { access_token, refresh_token } = tokenResult;
            
            const userProfile = await discordService.getUserProfile(access_token);
            if (!userProfile) {
                await webhookService.sendWebhookLog(guildId, '인증 실패', '사용자 프로필 가져오기 실패', 0xFF0000);
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "사용자 정보를 가져올 수 없습니다." });
            }
            
            const { username, global_name, id: userId, email } = userProfile;
            
            const userInfo = {
                userId: userId,
                username: username,
                globalName: global_name,
                email: email,
                ip: userIp,
                os: userOs,
                browser: userBrowser
            };
            
            const isBlacklisted = await dbService.checkIsBlacklisted(userId, userIp, email);
            if (isBlacklisted) {
                await webhookService.sendWebhookLog(guildId, '인증 실패', '블랙리스트에 등록된 사용자', 0xFF0000, [], userInfo);
                return res.status(403).render("auth_error", { ErrorCode: "7", Ctx: "블랙리스트에 등록되어 인증이 거부되었습니다." });
            }
            
            const serviceToken = helpers.generateRandomString(32);
            const existingUser = await dbService.checkUserExists(guildId, userId);
            
            if (!existingUser) {
                dbService.addUser(guildId, userId, refresh_token, email, serviceToken, userIp);
            } else {
                dbService.updateUser(guildId, userId, refresh_token, email, userIp);
            }
            
            let success = false;
            let retryCount = 0;
            const maxRetries = 3;
            
            while (retryCount < maxRetries && !success) {
                try {
                    const guild = await client.guilds.fetch(guildId);
                    let member;
                    
                    try {
                        member = await guild.members.fetch(userId);
                    } catch (memberError) {
                        
                        try {
                            const addMemberUrl = `https://discord.com/api/guilds/${guildId}/members/${userId}`;
                            const addMemberData = {
                                access_token: access_token
                            };
                            const addMemberHeaders = {
                                "Authorization": `Bot ${config.botToken}`,
                                "Content-Type": "application/json"
                            };
                            
                            const addMemberResponse = await axios.put(addMemberUrl, addMemberData, { headers: addMemberHeaders });
                            
                            if (addMemberResponse.status === 201 || addMemberResponse.status === 204) {
                                console.log(`사용자가 성공적으로 서버에 추가되었습니다: ${userId}`);
                                member = await guild.members.fetch(userId);
                                
                                await webhookService.sendWebhookLog(guildId, '인증 정보', '사용자가 서버에 자동으로 추가되었습니다.', 0x4287f5, [], userInfo);
                            } else {
                                throw new Error(`사용자 추가 실패. 상태 코드: ${addMemberResponse.status}`);
                            }
                        } catch (addError) {
                            console.error('서버에 사용자 추가 실패:', addError);
                            await webhookService.sendWebhookLog(guildId, '인증 실패', '사용자를 서버에 추가하지 못했습니다.', 0xFF0000, [
                                { name: '오류 내용', value: `\`${addError.message || '알 수 없는 오류'}\`` }
                            ], userInfo);
                            return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "사용자를 서버에 추가하지 못했습니다." });
                        }
                    }
                    
                    try {
                        const role = await guild.roles.fetch(roleIdStr);
                        
                        if (!role) {
                            await webhookService.sendWebhookLog(guildId, '인증 실패', '설정된 역할이 서버에 존재하지 않음', 0xFF0000, [
                                { name: '역할 ID', value: `\`${roleIdStr}\`` }
                            ], userInfo);
                            return res.status(404).render("auth_error", { 
                                ErrorCode: "5", 
                                Ctx: "설정된 역할이 서버에 존재하지 않습니다. 서버 관리자에게 문의하세요." 
                            });
                        }
                        
                        await member.roles.add(roleIdStr);
                        success = true;
                    } catch (roleError) {
                        if (roleError.code === 10011) {
                            await webhookService.sendWebhookLog(guildId, '인증 실패', '설정된 역할이 서버에 존재하지 않음', 0xFF0000, [
                                { name: '역할 ID', value: `\`${roleIdStr}\`` },
                                { name: '오류 코드', value: `\`${roleError.code}\`` }
                            ], userInfo);
                            return res.status(404).render("auth_error", { 
                                ErrorCode: "5", 
                                Ctx: "설정된 역할이 서버에 존재하지 않습니다. 서버 관리자에게 문의하세요." 
                            });
                        } else {
                            throw roleError;
                        }
                    }
                } catch (apiError) {
                    if (apiError.httpStatus === 429) {
                        const retryAfter = apiError.retry_after || 5;
                        await new Promise(resolve => setTimeout(resolve, (retryAfter + 1) * 1000));
                        retryCount++;
                    } else {
                        console.error('역할 추가 실패:', apiError);
                        break;
                    }
                }
            }
            
            if (!success) {
                await webhookService.sendWebhookLog(guildId, '인증 실패', '역할 적용 실패', 0xFF0000, [], userInfo);
                return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "역할 적용 중 오류가 발생했습니다." });
            }
            
            await webhookService.sendWebhookLog(guildId, '인증 로그', `사용자가 인증을 완료했습니다.`, 0x4CD964, [
                { name: '서버 ID', value: `\`${guildId}\`` },
                { name: '역할 ID', value: `\`${roleIdStr}\`` }
            ], userInfo);
            
            await dbService.addAuthLog(guildId, userId, '인증 성공: 역할 지급 완료', {
                ip: userIp,
                email,
                username,
                globalName: global_name
            });
            
            return res.status(200).render("auth_success");
        } catch (error) {
            console.error('인증 처리 오류:', error);
            await webhookService.sendWebhookLog(guildId, '인증 실패', '처리 중 오류 발생', 0xFF0000, [
                { name: '오류 내용', value: `\`${error.message || '알 수 없는 오류'}\`` }
            ]);
            return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
        }
    } catch (error) {
        console.error('인증 처리 중 예외 발생:', error);
        try {
            await webhookService.sendWebhookLog(guildId, '인증 실패', '처리 중 예외 발생', 0xFF0000, [
                { name: '오류 내용', value: `\`${error.message || '알 수 없는 오류'}\`` }
            ]);
        } catch (webhookError) {
            console.error('웹훅 전송 실패:', webhookError);
        }
        return res.status(500).render("auth_error", { ErrorCode: "0", Ctx: "인증 프로세스 중 오류가 발생했습니다." });
    }
}

// V1.3.2