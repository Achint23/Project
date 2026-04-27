/**
 * Quick test script for the Nvidia LLM API.
 * Run with: node scripts/test-nvidia.mjs
 * Make sure NVIDIA_API_KEY is set in your environment or .env.local
 */

import { readFileSync } from "fs";
import { resolve } from "path";

// Load .env.local manually (no dotenv dependency needed)
try {
  const envPath = resolve(process.cwd(), ".env.local");
  const lines = readFileSync(envPath, "utf-8").split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
    if (!process.env[key]) process.env[key] = val;
  }
} catch {
  console.warn("No .env.local found, relying on existing environment variables\n");
}

const apiKey = process.env.NVIDIA_API_KEY;
const baseUrl = process.env.NVIDIA_BASE_URL || "https://integrate.api.nvidia.com/v1";
const model = process.env.NVIDIA_MODEL || "meta/llama-3.1-70b-instruct";

if (!apiKey) {
  console.error("ERROR: NVIDIA_API_KEY is not set");
  process.exit(1);
}

console.log("=== Nvidia LLM API Test ===");
console.log(`Base URL : ${baseUrl}`);
console.log(`Model    : ${model}`);
console.log(`API Key  : ${apiKey.slice(0, 8)}...${apiKey.slice(-4)}\n`);

const endpoint = `${baseUrl}/chat/completions`;

// 1. Basic connectivity + auth check
console.log("1. Sending test prompt...");
const startTime = Date.now();

try {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: "You are a helpful assistant. Reply concisely." },
        { role: "user", content: 'Reply with exactly: {"status":"ok"}' },
      ],
      temperature: 0.1,
      max_tokens: 32,
      response_format: { type: "json_object" },
    }),
    signal: AbortSignal.timeout(30_000), // 30s timeout
  });

  const elapsed = Date.now() - startTime;
  console.log(`   HTTP status : ${response.status} ${response.statusText}`);
  console.log(`   Latency     : ${elapsed}ms`);

  if (!response.ok) {
    const body = await response.text();
    console.error(`\nERROR: API returned ${response.status}`);
    console.error(`Response body: ${body}`);

    if (response.status === 401) {
      console.error("\nDiagnosis: Invalid API key.");
    } else if (response.status === 429) {
      console.error("\nDiagnosis: Rate limit hit. Check your Nvidia API quota.");
    } else if (response.status === 504) {
      console.error("\nDiagnosis: Gateway timeout (504). The Nvidia endpoint is overloaded or down.");
      console.error("  - Try again in a few minutes");
      console.error("  - Check https://status.nvidia.com or the Nvidia NIM documentation");
      console.error(`  - Consider switching NVIDIA_MODEL to a less loaded model`);
    }
    process.exit(1);
  }

  const data = await response.json();
  const content = data.choices?.[0]?.message?.content || "(empty)";
  const usage = data.usage;

  console.log(`   Response    : ${content}`);
  if (usage) {
    console.log(`   Tokens used : ${usage.prompt_tokens} prompt + ${usage.completion_tokens} completion`);
  }

  console.log("\n✓ Nvidia API is working correctly.\n");

  // 2. Check if the model supports the transaction parsing use-case
  console.log("2. Testing transaction parsing prompt...");
  const parseStart = Date.now();

  const parseResponse = await fetch(endpoint, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        {
          role: "system",
          content: "Extract transaction details from bank alert emails. Return JSON only.",
        },
        {
          role: "user",
          content:
            "Email: 'Dear Customer, Rs.500.00 has been debited from your account ending 1234 on 14-Mar-2026 at SWIGGY. Available balance: Rs.12345.00'. Extract: amount, currency, merchant, date, last4.",
        },
      ],
      temperature: 0.1,
      max_tokens: 256,
      response_format: { type: "json_object" },
    }),
    signal: AbortSignal.timeout(30_000),
  });

  const parseElapsed = Date.now() - parseStart;
  console.log(`   HTTP status : ${parseResponse.status} ${parseResponse.statusText}`);
  console.log(`   Latency     : ${parseElapsed}ms`);

  if (!parseResponse.ok) {
    const body = await parseResponse.text();
    console.error(`   ERROR: ${body}`);
  } else {
    const parseData = await parseResponse.json();
    const parseContent = parseData.choices?.[0]?.message?.content || "(empty)";
    console.log(`   Response    : ${parseContent}`);
    console.log("\n✓ Transaction parsing prompt works.\n");
  }
} catch (err) {
  const elapsed = Date.now() - startTime;
  console.error(`\nERROR after ${elapsed}ms: ${err.message}`);

  if (err.name === "TimeoutError") {
    console.error("\nDiagnosis: Request timed out after 30s.");
    console.error("  - The Nvidia API is very slow or unreachable");
    console.error("  - The 504 in your app is the same issue");
  } else if (err.code === "ENOTFOUND") {
    console.error("\nDiagnosis: DNS resolution failed for the API host.");
    console.error("  - Check your internet connection");
    console.error("  - Verify NVIDIA_BASE_URL is correct");
  }
  process.exit(1);
}
