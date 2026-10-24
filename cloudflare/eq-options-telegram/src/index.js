export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return Response.json({ok:true,service:"eq-options-telegram",brand:"EQ Options",telegramConfigured:Boolean(env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_WEBHOOK_SECRET)});
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
