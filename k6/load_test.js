import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:80";

export const options = {
  stages: [
    { duration: "30s", target: 50 },
    { duration: "60s", target: 50 },
    { duration: "30s", target: 200 },
    { duration: "60s", target: 200 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<3000"],
    http_req_failed: ["rate<0.05"],
  },
};

export default function () {
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, { "health is 200": (r) => r.status === 200 });

  const listRes = http.get(`${BASE_URL}/urls`);
  check(listRes, { "list urls is 200": (r) => r.status === 200 });

  const shortenRes = http.post(
    `${BASE_URL}/shorten`,
    JSON.stringify({
      original_url: `https://example.com/load-test/${Math.random()}`,
      title: "Load Test URL",
    }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(shortenRes, { "shorten is 201": (r) => r.status === 201 });

  if (shortenRes.status === 201) {
    const body = JSON.parse(shortenRes.body);
    const redirectRes = http.get(`${BASE_URL}/${body.short_code}`, {
      redirects: 0,
    });
    check(redirectRes, { "redirect is 302": (r) => r.status === 302 });
  }

  sleep(1);
}
