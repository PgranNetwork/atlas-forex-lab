export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return Response.json({ok:true,service:"eq-options-telegram",brand:"EQ Options",telegramConfigured:Boolean(env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_WEBHOOK_SECRET)});
    }
    if (request.method === "GET" && url.pathname === "/setup") {
      return new Response(`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>EQ Options setup</title></head><body style="font:16px system-ui;max-width:520px;margin:40px auto;padding:16px"><h1>EQ Options bot setup</h1><p>First add the Telegram bot token as the <code>TELEGRAM_BOT_TOKEN</code> secret in Cloudflare. Then enter the one-time setup code supplied by your project maintainer.</p><form method="post" action="/setup"><label for="code">One-time setup code</label><br><input id="code" name="code" required autocomplete="off" style="width:100%;padding:12px;margin:12px 0;box-sizing:border-box"><button style="padding:12px 18px">Configure Telegram webhook</button></form><p>This page never asks for or displays your bot token.</p></body></html>`,{headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store"}});
    }
    if (request.method === "POST" && url.pathname === "/setup") {
      if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_WEBHOOK_SECRET || !env.SETUP_CODE) return new Response("Required Worker secrets are missing. Configure them in Cloudflare first.",{status:503});
      let form; try { form=await request.formData(); } catch { return new Response("Invalid form",{status:400}); }
      if (!constantTimeEqual(String(form.get("code")||""),env.SETUP_CODE)) return new Response("Invalid setup code",{status:403});
      const hookUrl=new URL("/telegram",url.origin).toString();
      const result=await fetch("https://api.telegram.org/bot"+env.TELEGRAM_BOT_TOKEN+"/setWebhook",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({url:hookUrl,secret_token:env.TELEGRAM_WEBHOOK_SECRET,allowed_updates:["message"],drop_pending_updates:false})});
      let resultBody={}; try { resultBody=await result.json(); } catch {}
      if(!result.ok||resultBody.ok!==true){const code=Number(resultBody.error_code)||result.status||502;const description=String(resultBody.description||"No Telegram error description returned").slice(0,240);console.error("Telegram setWebhook failed",code,description);return new Response("Telegram webhook setup failed (code "+code+"): "+description+" . The bot token is never shown here.",{status:502,headers:{"content-type":"text/plain; charset=utf-8","cache-control":"no-store"}});}
      return new Response("Webhook configured successfully. Open Telegram and send /start to @Eqoptions_bot. The setup code should now be treated as sensitive until the maintainer disables setup.",{headers:{"content-type":"text/plain; charset=utf-8","cache-control":"no-store"}});
    }
    if(request.method!=="POST"||url.pathname!=="/telegram") return new Response("Not found",{status:404});
    if(!env.TELEGRAM_BOT_TOKEN||!env.TELEGRAM_WEBHOOK_SECRET) return new Response("Bot not configured",{status:503});
    const suppliedSecret=request.headers.get("X-Telegram-Bot-Api-Secret-Token")||"";
    if(!constantTimeEqual(suppliedSecret,env.TELEGRAM_WEBHOOK_SECRET)) return new Response("Unauthorized",{status:401});
    let update; try { update=await request.json(); } catch { return new Response("Bad JSON",{status:400}); }
    const message=update?.message; const chatId=message?.chat?.id; const text=typeof message?.text==="string"?message.text.trim():"";
    if(!chatId||!text.startsWith("/")) return new Response("OK");
    const command=text.split(/\s+/,1)[0].split("@")[0].toLowerCase(); let reply;
    switch(command){
      case "/start": reply="Welcome to EQ Options.\n\nExperimental forex and gold market research — not financial advice. Forecasts can be wrong and are not guaranteed. No live trading is available.\n\nCommands: /help /brokers /referral_status /forecast";break;
      case "/help": reply="/start — introduction\n/forecast — forecast service status\n/brokers — configured broker links\n/referral_status — referral verification status\n\nEQ Options is for research only. No live trading or guaranteed-profit claims.";break;
      case "/forecast": reply="Forecast service is being prepared. Live market data and validated forecasts are not connected yet, so EQ Options will not invent a live signal. Please check back later.";break;
      case "/brokers": reply="No broker links are configured yet. Any future affiliate links will be clearly disclosed.";break;
      case "/referral_status": reply="Broker referral verification is not connected yet. A click or submitted account ID does not prove registration or qualification. We will not mark referrals verified without authoritative broker evidence.";break;
      default: reply="I didn't recognize that command. Send /help to see available commands.";
    }
    const telegramResponse=await fetch("https://api.telegram.org/bot"+env.TELEGRAM_BOT_TOKEN+"/sendMessage",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({chat_id:chatId,text:reply,disable_web_page_preview:true})});
    if(!telegramResponse.ok){console.error("Telegram sendMessage failed",telegramResponse.status);return new Response("Telegram API error",{status:502});}
    return new Response("OK");
  }
};
function constantTimeEqual(a,b){const e=new TextEncoder(),x=e.encode(a),y=e.encode(b);if(x.length!==y.length)return false;let d=0;for(let i=0;i<x.length;i++)d|=x[i]^y[i];return d===0;}
