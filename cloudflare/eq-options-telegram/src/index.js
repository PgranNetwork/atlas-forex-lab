export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(ingestLatestBars(env));
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/api/markets") {
      if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
        return Response.json({ok:false,status:"unavailable",reason:"database_not_configured"}, {status:503});
      }
      try {
        const rows = await readLatestBars(env);
        return Response.json({ok:true,status:rows.length ? "available" : "empty",bars:rows});
      } catch (error) {
        const diagnostic = error instanceof Error ? error.message : "unknown_database_error";
        const key = typeof env.SUPABASE_SERVICE_ROLE_KEY === "string" ? env.SUPABASE_SERVICE_ROLE_KEY.trim() : "";
        const url = typeof env.SUPABASE_URL === "string" ? env.SUPABASE_URL.trim() : "";
        const jwtClaims = (() => {
          try {
            if (!key.startsWith("eyJ")) return null;
            const segment = key.split(".")[1];
            if (!segment) return null;
            const normalized = segment.replace(/-/g, "+").replace(/_/g, "/");
            return JSON.parse(atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=")));
          } catch { return null; }
        })();
        const safeDiagnostics = {
          key_kind: key.startsWith("sb_secret_") ? "modern_secret" : key.startsWith("eyJ") ? "legacy_jwt" : key ? "unknown_format" : "missing",
          key_length: key.length,
          jwt_role: typeof jwtClaims?.role === "string" ? jwtClaims.role : "not_detected",
          jwt_project_ref: typeof jwtClaims?.ref === "string" ? jwtClaims.ref : "not_present",
          url_project_ref: (() => { try { return new URL(url).hostname.split(".")[0]; } catch { return "invalid_url"; } })()
        };
        console.error("Market API database failure", diagnostic, safeDiagnostics);
        return Response.json({ok:false,status:"unavailable",reason:diagnostic,diagnostics:safeDiagnostics}, {status:503});
      }
    }
    if (request.method === "GET" && url.pathname === "/api/ingestion-status") {
      if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
        return Response.json({ok:false,status:"unavailable",reason:"database_not_configured"},{status:503});
      }
      try {
        const base = env.SUPABASE_URL.replace(/\/$/, "");
        const query = new URLSearchParams({select:"source,instrument,checked_at,healthy,latency_ms,details",order:"checked_at.desc",limit:"12"});
        const response = await fetch(base + "/rest/v1/data_source_health?" + query.toString(), {headers:supabaseHeaders(env)});
        if (!response.ok) throw new Error("health_query_http_" + response.status);
        const rows = await response.json();
        return Response.json({
          ok:true,
          status:rows.length ? "records_found" : "no_records",
          configuration:{
            supabase_url_present:Boolean(env.SUPABASE_URL),
            supabase_key_present:Boolean(env.SUPABASE_SERVICE_ROLE_KEY),
            twelve_data_key_present:Boolean(env.TWELVEDATA_API_KEY),
            url_project_ref:(() => { try { return new URL(env.SUPABASE_URL).hostname.split(".")[0]; } catch { return "invalid_url"; } })()
          },
          checks:rows
        });
      } catch (error) {
        return Response.json({ok:false,status:"unavailable",reason:error instanceof Error ? error.message : "health_query_failed"},{status:503});
      }
    }
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
        [{text:"ℹ️ Help"}],
        [{text:"🏠 Main menu"}]
      ],
      resize_keyboard: true,
      is_persistent: true,
      input_field_placeholder: "Choose an option…"
    };
    const helpText = "Here’s what you can do in EQ Options:\n\n📊 Forecast — current forecast-service status\n💹 Markets — market-data coverage\n🤝 Brokers — disclosed broker links when available\n👤 Referral status — verification integration status\n\nResearch only. No live trading or guaranteed-profit claims.";
    const messages = {
      start: "Welcome to EQ Options 👋\n\nYour home for experimental forex and gold market research.\n\nChoose an option below to get started. Forecasts are not guaranteed, and this bot does not place trades.",
      help: helpText,
      forecast: "📊 Forecast status\n\nThe forecasting service is being prepared. Live market data and validated forecasts are not connected yet, so we won’t invent a signal. We’ll show forecasts only after data and evaluation checks are in place.",
      markets: "💹 Market coverage\n\nChecking the latest stored market data…",
      brokers: "🤝 Broker links\n\nNo broker links are configured yet. Any future affiliate links will be clearly disclosed. EQ Options does not need your broker password or one-time codes.",
      referral_status: "👤 Referral status\n\nReferral verification is not connected yet. A click or submitted account ID does not prove registration or qualification. We’ll only mark referrals verified using authoritative broker evidence."
    };
    const normalize = value => {
      const v = String(value || "").trim().toLowerCase().replace(/\s+/g," ");
      if (v === "/start" || v === "start" || v === "🏠 main menu" || v === "🏠 home") return "start";
      if (v === "⬅️ back" || v === "back") return "back";
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
      const key = action === "back" ? "start" : (action && messages[action] ? action : "help");
      let responseText = messages[key];
      let markup = {keyboard:replyKeyboard.keyboard,resize_keyboard:true,is_persistent:true,input_field_placeholder:"Choose an option…"};
      if (key === "markets") {
        try {
          responseText = (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY)
            ? "💹 Market coverage\\n\\nMarket data is not configured yet. No prices are being displayed as live."
            : formatMarketSnapshot(await readLatestBars(env));
        } catch {
          responseText = "💹 Market coverage\\n\\nMarket data is temporarily unavailable. Please try again later.";
        }
        markup = {inline_keyboard:[
          [{text:"🔄 Refresh",callback_data:"markets"},{text:"📊 Forecast status",callback_data:"forecast"}],
          [{text:"⬅️ Back",callback_data:"start"},{text:"🏠 Main menu",callback_data:"start"}]
        ]};
      }
      await telegram("sendMessage", {chat_id:chatId,text:responseText,reply_markup:markup,disable_web_page_preview:true});
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
    const key = action === "back" ? "start" : action;
    const replyMarkup = {keyboard:replyKeyboard.keyboard,resize_keyboard:true,is_persistent:true,input_field_placeholder:"Choose an option…"};
    let responseText = messages[key];
    if (key === "markets") {
      try {
        if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
          responseText = "💹 Market coverage\n\nMarket data is not configured yet. No prices are being displayed as live.";
        } else {
          const rows = await readLatestBars(env);
          responseText = formatMarketSnapshot(rows);
        }
      } catch {
        responseText = "💹 Market coverage\n\nMarket data is temporarily unavailable. Please try again later.";
      }
    }
    const inline = key === "markets" ? {inline_keyboard:[
      [{text:"🔄 Refresh",callback_data:"markets"},{text:"📊 Forecast status",callback_data:"forecast"}],
      [{text:"ℹ️ Help",callback_data:"help"}]
    ]} : undefined;
    await telegram("sendMessage",{
      chat_id:chatId,
      text:responseText,
      reply_markup:inline ? {...replyMarkup, ...inline} : replyMarkup,
      disable_web_page_preview:true
    });
    return new Response("OK");
  }
};
function constantTimeEqual(a,b){const e=new TextEncoder(),x=e.encode(a),y=e.encode(b);if(x.length!==y.length)return false;let d=0;for(let i=0;i<x.length;i++)d|=x[i]^y[i];return d===0;}

async function readLatestBars(env) {
        const base = env.SUPABASE_URL.replace(/\/$/, "");
  const query = new URLSearchParams({
    select: "instrument,timeframe,open_time,open_price,high_price,low_price,close_price,source,received_at",
    timeframe: "eq.M1",
    order: "open_time.desc",
    limit: "100"
  });
  const response = await fetch(base + "/rest/v1/market_bars?" + query.toString(), {
    headers: supabaseHeaders(env)
  });
  if (!response.ok) {
    let code = "unknown";
    try {
      const error = await response.json();
      if (typeof error?.code === "string") code = error.code;
      else if (typeof error?.message === "string") code = error.message.slice(0, 80).replace(/[^a-zA-Z0-9 _-]/g, "");
    } catch {}
    throw new Error("supabase_http_" + response.status + "_" + code);
  }
  const rows = await response.json();
  const latest = new Map();
  for (const row of rows) if (!latest.has(row.instrument)) latest.set(row.instrument, row);
  return Array.from(latest.values());
}
function formatMarketSnapshot(rows) {
  if (!rows.length) return "💹 Market coverage\n\nNo market candles have been stored yet. The feed is not confirmed live, so no price is shown.";
  const now = Date.now();
  const lines = rows.map(row => {
    const age = Math.max(0, Math.round((now - Date.parse(row.open_time)) / 60000));
    const freshness = age <= 3 ? "FRESH" : age <= 10 ? "DELAYED" : "STALE";
    return (row.instrument === "XAUUSD" ? "🟡 " : "💱 ") + row.instrument + " — " + Number(row.close_price).toString() +
      "\n   " + row.timeframe + " · " + freshness + " · candle " + row.open_time;
  });
  return "💹 Latest stored market candles\n\n" + lines.join("\n\n") +
    "\n\nSource: provider recorded in database. These are market snapshots, not trading signals.";
}
async function ingestLatestBars(env) {
  if (!env.TWELVEDATA_API_KEY || !env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    console.log("Market ingestion skipped: required provider/database secrets are not configured.");
    return;
  }
  const instruments = ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD"];
  for (const symbol of instruments) {
    const started = Date.now();
    let healthy = false;
    try {
      const params = new URLSearchParams({
        symbol, interval:"1min", outputsize:"3", order:"ASC", timezone:"UTC", apikey:env.TWELVEDATA_API_KEY
      });
      const response = await fetch("https://api.twelvedata.com/time_series?" + params.toString());
      const payload = await response.json();
      if (!response.ok || payload.status === "error" || !Array.isArray(payload.values)) {
        throw new Error("Provider returned no usable candle values");
      }
      const bars = payload.values.map(row => {
        const open = Number(row.open), high = Number(row.high), low = Number(row.low), close = Number(row.close);
        const time = new Date(row.datetime.replace(" ", "T") + "Z");
        if (![open,high,low,close].every(Number.isFinite) || Math.min(open,high,low,close) <= 0 ||
            high < Math.max(open,close,low) || low > Math.min(open,close,high) || Number.isNaN(time.getTime())) {
          throw new Error("Provider returned malformed OHLC data");
        }
        return {instrument:symbol.replace("/",""), timeframe:"M1", open_time:time.toISOString(),
          open_price:open, high_price:high, low_price:low, close_price:close,
          volume:row.volume ? Number(row.volume) : null, source:"twelvedata", received_at:new Date().toISOString()};
      });
        const base = env.SUPABASE_URL.replace(/\/$/, "");
      const responseDb = await fetch(base + "/rest/v1/market_bars?on_conflict=instrument,timeframe,open_time,source", {
        method:"POST",
        headers:{...supabaseHeaders(env), "Content-Type":"application/json",Prefer:"resolution=ignore-duplicates,return=minimal"},
        body:JSON.stringify(bars)
      });
      if (!responseDb.ok) throw new Error("Database rejected market bars");
      healthy = true;
    } catch (error) {
      console.log("Ingestion failed for", symbol, error instanceof Error ? error.message : "unknown error");
    }
    try {
      const healthResponse = await fetch(env.SUPABASE_URL.replace(/\/$/, "") + "/rest/v1/data_source_health", {
        method:"POST",
        headers:{...supabaseHeaders(env), "Content-Type":"application/json",Prefer:"return=minimal"},
        body:JSON.stringify([{source:"twelvedata",instrument:symbol.replace("/",""),healthy,
          latency_ms:Date.now()-started,details:{interval:"1min"}}])
      });
      if (!healthResponse.ok) {
        const errorBody = await healthResponse.text().catch(() => "");
        console.error("Health write failed", symbol, healthResponse.status, errorBody.slice(0,160));
      }
    } catch { /* keep scheduled ingestion isolated per instrument */ }
  }
}

function supabaseHeaders(env) {
  const key = env.SUPABASE_SERVICE_ROLE_KEY;
  const headers = { apikey: key };
  // Modern Supabase secret keys (sb_secret_...) are opaque API keys, not JWTs.
  // Sending one as Authorization: Bearer causes Supabase Auth to reject it.
  // Legacy service_role keys are JWTs and still require the Bearer header.
  if (typeof key === "string" && !key.startsWith("sb_secret_")) {
    headers.Authorization = "Bearer " + key;
  }
  return headers;
}
