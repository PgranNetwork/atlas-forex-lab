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
    const replyKeyboard = {
      keyboard: [
        [{text:"📊 Forecast"}, {text:"💹 Markets"}],
        [{text:"👤 Referral status"}, {text:"🤝 Brokers"}],
        [{text:"ℹ️ Help"}]
      ],
      resize_keyboard: true,
      is_persistent: true,
      input_field_placeholder: "Choose an option…"
    };
    const inlineKeyboard = {
      inline_keyboard: [
        [{text:"📈 Forecast status", callback_data:"forecast"}, {text:"💹 Market coverage", callback_data:"markets"}],
        [{text:"🤝 Broker links", callback_data:"brokers"}, {text:"👤 Referral status", callback_data:"referral_status"}],
        [{text:"ℹ️ Help", callback_data:"help"}]
      ]
    };
    const helpText = "Here’s what you can do in EQ Options:\\n\\n📊 Forecast — current forecast-service status\\n💹 Markets — market-data coverage\\n🤝 Brokers — disclosed broker links when available\\n👤 Referral status — verification integration status\\n\\nResearch only. No live trading or guaranteed-profit claims.";
    const messages = {
      start: "Welcome to EQ Options 👋\\n\\nYour home for experimental forex and gold market research.\\n\\nChoose an option below to get started. Forecasts are not guaranteed, and this bot does not place trades.",
      help: helpText,
      forecast: "📊 Forecast status\\n\\nThe forecasting service is being prepared. Live market data and validated forecasts are not connected yet, so we won’t invent a signal. We’ll show forecasts only after data and evaluation checks are in place.",
      markets: "💹 Market coverage\\n\\nLive market feeds are not connected yet. Planned coverage includes major FX pairs and gold (XAUUSD). We’ll identify the data source and freshness before presenting market values.",
      brokers: "🤝 Broker links\\n\\nNo broker links are configured yet. Any future affiliate links will be clearly disclosed. EQ Options does not need your broker password or one-time codes.",
      referral_status: "👤 Referral status\\n\\nReferral verification is not connected yet. A click or submitted account ID does not prove registration or qualification. We’ll only mark referrals verified using authoritative broker evidence."
    };
    const normalize = value => {
      const v = String(value || "").trim().toLowerCase().replace(/\\s+/g," ");
      if (v === "/start" || v === "start" || v === "🏠 home") return "start";
      if (v === "/help" || v === "help" || v === "ℹ️ help") return "help";
      if (v === "/forecast" || v === "forecast" || v === "📊 forecast" || v === "📈 forecast status") return "forecast";
      if (v === "markets" || v === "💹 markets" || v === "💹 market coverage") return "markets";
      if (v === "/brokers" || v === "brokers" || v === "🤝 brokers" || v === "🤝 broker links") return "brokers";
      if (v === "/referral_status" || v === "referral status" || v === "👤 referral status") return "referral_status";
      return null;
    };
    async function telegram(method, payload) {
      const response = await fetch("https://api.telegram.org/bot"+env.TELEGRAM_BOT_TOKEN+"/"+method, {
        method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify(payload)
      });
      const data = await response.json().catch(()=>({}));
      if (!response.ok || data.ok !== true) {
        console.error("Telegram API request failed", method, response.status, data.error_code || "");
        return {ok:false};
      }
      return {ok:true,result:data.result};
    }
    if (update?.callback_query) {
      const cq = update.callback_query;
      const action = normalize(cq.data);
      await telegram("answerCallbackQuery", {callback_query_id:cq.id});
      const chatId = cq.message?.chat?.id;
      if (!chatId) return new Response("OK");
      const key = action === "start" ? "start" : (action && messages[action] ? action : "help");
      await telegram("sendMessage", {
        chat_id:chatId,
        text:messages[key],
        reply_markup:key === "start" ? {keyboard:replyKeyboard.keyboard,resize_keyboard:true,is_persistent:true,input_field_placeholder:"Choose an option…"} : inlineKeyboard,
        disable_web_page_preview:true
      });
      return new Response("OK");
    }
    const message=update?.message;
    const chatId=message?.chat?.id;
    const incoming=typeof message?.text==="string"?message.text.trim():"";
    if(!chatId) return new Response("OK");
    if (!incoming) {
      await telegram("sendMessage",{chat_id:chatId,text:"Please choose an option from the menu below, or send /help.",reply_markup:replyKeyboard,disable_web_page_preview:true});
      return new Response("OK");
    }
    const action = normalize(incoming);
    if (!action) {
      await telegram("sendMessage",{chat_id:chatId,text:"I didn’t recognize that option. Choose one of the menu buttons below, or tap Help.",reply_markup:replyKeyboard,disable_web_page_preview:true});
      return new Response("OK");
    }
    const key = action;
    const replyMarkup = key === "start" ? {
      keyboard:replyKeyboard.keyboard,resize_keyboard:true,is_persistent:true,input_field_placeholder:"Choose an option…"
    } : inlineKeyboard;
    await telegram("sendMessage",{
      chat_id:chatId,
      text:messages[key],
      reply_markup:replyMarkup,
      disable_web_page_preview:true
    });
    return new Response("OK");
  }
};
function constantTimeEqual(a,b){const e=new TextEncoder(),x=e.encode(a),y=e.encode(b);if(x.length!==y.length)return false;let d=0;for(let i=0;i<x.length;i++)d|=x[i]^y[i];return d===0;}
