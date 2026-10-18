# MCP-серверы для Amazon-агентов (не включены по умолчанию)

Это не скиллы, а работающие программы с доступом к вашим аккаунтам, поэтому в плагины они не вшиты: ключи у вас, подключение осознанное. Скиллы `amazon-ads` (агент PPC), `amzscout-research` (SEO-Listings) и др. работают только когда соответствующий MCP подключён. Добавляйте в `.mcp.json` проекта или `claude mcp add`; значения ключей берите из своих переменных окружения, в репозиторий их не коммитьте.

| Сервер | Что даёт | Источник | Подключение |
|---|---|---|---|
| Helium 10 | Cerebro, Xray, Listing Builder и др. | helium10/Helium10-MCP | `{"mcpServers":{"helium10-mcp":{"url":"https://mcp.helium10.com/mcp","headers":{"Authorization":"h10_mcp_<токен>"}}}}` (токен без `Bearer`; без токена вход через OAuth) |
| AMZScout | анализ ниши и ASIN, ключи, PPC | amzscout-corp/amzscout-skill-mcp | `{"mcpServers":{"amzscout":{"type":"streamable-http","url":"https://chatbot.amzscout.net/mcp","headers":{"Authorization":"Bearer <ключ>"}}}}` |
| Marketplace Ad Pros | отчёты и управление Amazon Ads | MarketplaceAdPros/skill-amazon-ads | `claude mcp add map --transport http https://app.marketplaceadpros.com/mcp` |
| DataDive | ниши, ключи, конкуренты, Rank Radar | Data-Dive-Tools/datadive-mcp | `claude mcp add datadive --env DATADIVE_API_KEY=<ключ> -- npx -y @datadive-tools/mcp` |
| Seller Central (SP-API) | каталог и листинги вашего аккаунта через SP-API | bhavykhatri/amazon-seller-mcp | `npx -y seller-central-mcp`; env: `SP_API_CLIENT_ID`, `SP_API_CLIENT_SECRET`, `SP_API_REFRESH_TOKEN`, `SP_API_SELLER_ID`, опционально `SP_API_MARKETPLACE_ID`, `SP_API_ENDPOINT` (по умолчанию Индия/amazon.in) |
| Amazon Ads API (Openbridge) | Amazon Advertising API через MCP | KuudoAI/amazon_ads_mcp | Docker/Python-сервер, настройка в `INSTALL.md` репозитория; нужны Amazon Ads credentials |

Не подключается как MCP:
- `ahamdjin/SP-API` - локальный Next.js-стенд для проверки SP-API-ключей и каталожных/FBA-запросов. Запускается отдельно (`npm install && npm run dev`), агенту не нужен.
- `amzn/selling-partner-api-models` - официальные модели API; нужные четыре файла лежат в скилле `sp-api-reference`.

Перед первым подключением, которое пишет в аккаунт (листинги, цены, ставки), агент обязан получить явное подтверждение пользователя; подключение только на чтение предпочтительнее.
