const DEFAULT_CATEGORY_RULES = {
  sustainability: ["sustain", "circular", "climate", "recycl", "eco"],
  innovation: ["innovation", "launch", "product", "solution", "ai", "prototype"],
  events: ["event", "conference", "expo", "webinar", "booth", "panel"],
  awards: ["award", "recognition", "won", "shortlist", "honor", "prize"],
  partnerships: ["partner", "collaborat", "together", "alliance"],
  hiring: ["hiring", "career", "role", "join our team", "apply"],
  thought_leadership: ["insight", "report", "whitepaper", "guide", "blog"],
  packaging: ["packag", "design", "material", "bottle", "reusable"],
};

const fileInput = document.getElementById("fileInput");
const loadSampleBtn = document.getElementById("loadSampleBtn");
const controlsForm = document.getElementById("controlsForm");
const alertsEl = document.getElementById("alerts");
const summaryPanel = document.getElementById("summaryPanel");
const topPostsPanel = document.getElementById("topPostsPanel");
const traitsPanel = document.getElementById("traitsPanel");

const postsAnalyzedEl = document.getElementById("postsAnalyzed");
const postsFetchedEl = document.getElementById("postsFetched");
const timeframeEl = document.getElementById("timeframe");
const topCategoriesEl = document.getElementById("topCategories");

const topPostsEl = document.getElementById("topPosts");
const traitCategoriesEl = document.getElementById("traitCategories");
const traitMediaEl = document.getElementById("traitMedia");
const traitDaysEl = document.getElementById("traitDays");
const traitHashtagsEl = document.getElementById("traitHashtags");
const traitAveragesEl = document.getElementById("traitAverages");

const topNInput = document.getElementById("topN");
const lookbackInput = document.getElementById("lookback");
const categoryConfigInput = document.getElementById("categoryConfig");

let rawPosts = [];

fileInput.addEventListener("change", handleFileUpload);
loadSampleBtn.addEventListener("click", handleSampleLoad);
controlsForm.addEventListener("submit", (event) => {
  event.preventDefault();
  runAnalysis();
});

async function handleSampleLoad() {
  try {
    const response = await fetch("sample-data.json");
    if (!response.ok) throw new Error("Unable to load sample data.");
    const data = await response.json();
    rawPosts = extractElements(data);
    showAlert("Loaded sample dataset with synthetic posts.", "info");
    runAnalysis();
  } catch (error) {
    showAlert(error.message, "error");
  }
}

function handleFileUpload(event) {
  const [file] = event.target.files || [];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (loadEvent) => {
    try {
      const parsed = JSON.parse(loadEvent.target.result);
      rawPosts = extractElements(parsed);
      if (!rawPosts.length) {
        throw new Error("File parsed, but no posts were found.");
      }
      showAlert(`Loaded ${rawPosts.length} posts from ${file.name}.`, "info");
      runAnalysis();
    } catch (error) {
      showAlert(`Could not parse file: ${error.message}`, "error");
    }
  };
  reader.readAsText(file);
}

function runAnalysis() {
  clearAlerts();
  if (!rawPosts.length) {
    showAlert("Load a JSON file or the sample data before analyzing.", "error");
    return;
  }

  const options = {
    topN: clampNumber(Number(topNInput.value) || 5, 1, 20),
    lookbackDays: clampNumber(Number(lookbackInput.value) || 365, 7, 730),
  };
  const categoryRules = parseCategoryConfig(categoryConfigInput.value);

  const normalized = rawPosts
    .map(normalizePost)
    .filter((post) => Boolean(post && post.createdAt));

  const result = analyzePosts(normalized, options, categoryRules);
  renderResult(result);
}

function analyzePosts(posts, options, categoryRules) {
  const now = new Date();
  const since = new Date(now.getTime() - options.lookbackDays * 86400000);

  const filtered = posts.filter(
    (post) => post.createdAt >= since && post.createdAt <= now,
  );

  const categorized = filtered.map((post) => ({
    post,
    categories: categorizePost(post, categoryRules),
  }));

  const categoryCounts = countCategories(categorized);

  const topPosts = [...filtered]
    .sort((a, b) => {
      const diff =
        (b.stats.engagementRate || 0) - (a.stats.engagementRate || 0);
      if (diff !== 0) return diff;
      return (b.stats.totalInteractions || 0) - (a.stats.totalInteractions || 0);
    })
    .slice(0, options.topN);

  const traits = summarizeTraits(topPosts, categoryRules);

  return {
    since,
    until: now,
    totalPostsFetched: posts.length,
    totalPostsAnalyzed: filtered.length,
    categorized,
    categoryCounts,
    topPosts,
    traits,
  };
}

function renderResult(result) {
  if (!result.totalPostsAnalyzed) {
    showAlert(
      "No posts fall within the selected timeframe. Try expanding the lookback window.",
      "error",
    );
    summaryPanel.hidden = true;
    topPostsPanel.hidden = true;
    traitsPanel.hidden = true;
    return;
  }

  const categoryLookup = new Map(
    result.categorized.map((entry) => [entry.post.id, entry.categories]),
  );

  postsAnalyzedEl.textContent = result.totalPostsAnalyzed;
  postsFetchedEl.textContent = `${result.totalPostsFetched} total posts loaded`;
  timeframeEl.textContent = `${formatDate(result.since)} → ${formatDate(result.until)}`;
  renderCategoryList(
    topCategoriesEl,
    result.categoryCounts,
    5,
    result.totalPostsAnalyzed,
  );

  topPostsEl.innerHTML = "";
  result.topPosts.forEach((post, index) => {
    const categories = categoryLookup.get(post.id) || ["general"];
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${index + 1}</td>
      <td>${formatDate(post.createdAt)}</td>
      <td>${formatPercent(post.stats.engagementRate)}</td>
      <td>${post.stats.totalInteractions}</td>
      <td>${categories.join(", ")}</td>
    `;
    topPostsEl.appendChild(row);
  });

  renderTraits(result.traits);

  summaryPanel.hidden = false;
  topPostsPanel.hidden = false;
  traitsPanel.hidden = false;
}

function renderTraits(traits) {
  renderKeyValueList(
    traitCategoriesEl,
    traits.categories,
    (value) => formatPercent(value),
  );
  renderKeyValueList(traitMediaEl, traits.mediaTypes, (value) =>
    formatPercent(value),
  );
  renderKeyValueList(traitDaysEl, traits.days, (value) => formatPercent(value));

  traitHashtagsEl.innerHTML = "";
  if (traits.hashtags && Object.keys(traits.hashtags).length) {
    Object.entries(traits.hashtags).forEach(([tag, count]) => {
      const li = document.createElement("li");
      li.textContent = `${tag} (${count})`;
      traitHashtagsEl.appendChild(li);
    });
  } else {
    traitHashtagsEl.innerHTML = "<li>No recurring hashtags detected.</li>";
  }

  traitAveragesEl.innerHTML = "";
  Object.entries(traits.averages).forEach(([label, value]) => {
    const li = document.createElement("li");
    li.textContent = `${label.replace(/_/g, " ")}: ${value}`;
    traitAveragesEl.appendChild(li);
  });
}

function renderCategoryList(element, counter, limit, totalPosts = null) {
  element.innerHTML = "";
  const entries = Object.entries(counter)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit);

  if (!entries.length) {
    element.innerHTML = "<li>No categories detected.</li>";
    return;
  }

  const denominator =
    totalPosts && totalPosts > 0
      ? totalPosts
      : entries.reduce((sum, [, value]) => sum + value, 0);
  entries.forEach(([category, value]) => {
    const li = document.createElement("li");
    li.textContent = `${category} • ${(value / denominator).toLocaleString(undefined, {
      style: "percent",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    })}`;
    element.appendChild(li);
  });
}

function renderKeyValueList(element, data, formatter) {
  element.innerHTML = "";
  const entries = Object.entries(data || {});
  if (!entries.length) {
    element.innerHTML = "<li>No data.</li>";
    return;
  }
  entries.forEach(([key, value]) => {
    const li = document.createElement("li");
    li.textContent = `${key}: ${formatter(value)}`;
    element.appendChild(li);
  });
}

function summarizeTraits(topPosts, categoryRules) {
  if (!topPosts.length) {
    return {
      categories: {},
      mediaTypes: {},
      days: {},
      hashtags: {},
      averages: {},
    };
  }

  const categorizedSubset = topPosts.map((post) => ({
    post,
    categories: categorizePost(post, categoryRules),
  }));

  const categoryCounts = countCategories(categorizedSubset);
  const total = topPosts.length;
  const mediaCounts = {};
  const dayCounts = {};
  const hashtagCounts = {};

  let totalWords = 0;
  let totalHashtags = 0;
  let links = 0;
  let mentions = 0;

  topPosts.forEach((post) => {
    const mediaKey = post.mediaType || "unspecified";
    mediaCounts[mediaKey] = (mediaCounts[mediaKey] || 0) + 1;

    const day = formatWeekday(post.createdAt);
    dayCounts[day] = (dayCounts[day] || 0) + 1;

    post.hashtags.forEach((tag) => {
      hashtagCounts[tag] = (hashtagCounts[tag] || 0) + 1;
    });

    totalWords += post.wordCount;
    totalHashtags += post.hashtags.length;

    if (post.containsLink) links += 1;
    if (post.containsMention) mentions += 1;
  });

  return {
    categories: normalizeCounts(categoryCounts, total),
    mediaTypes: normalizeCounts(mediaCounts, total),
    days: normalizeCounts(dayCounts, total),
    hashtags: takeTopEntries(hashtagCounts, 5),
    averages: {
      "word count": Math.round((totalWords / total) * 10) / 10,
      "hashtags per post": (totalHashtags / total).toFixed(2),
      "link rate": formatPercent(links / total),
      "mention rate": formatPercent(mentions / total),
    },
  };
}

function countCategories(categorizedPosts) {
  const counter = {};
  categorizedPosts.forEach((entry) => {
    entry.categories.forEach((category) => {
      counter[category] = (counter[category] || 0) + 1;
    });
  });
  return counter;
}

function normalizePost(raw) {
  try {
    const text = extractText(raw);
    const hashtags = extractHashtags(raw);

    const createdAt = extractDate(raw);
    const stats = extractStats(raw);

    const fallbackId = Math.random().toString(36).slice(2, 10);
    const base = {
      id:
        raw.id ||
        raw.urn ||
        raw.postUrn ||
        (typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : fallbackId),
      urn: raw.urn || raw.id || "",
      author: raw.author || raw.actor || "",
      text,
      hashtags,
      lifecycleState: raw.lifecycleState || raw.state || "PUBLISHED",
      mediaType: extractMediaType(raw),
      visibility: extractVisibility(raw),
      createdAt,
      containsLink: /https?:\/\//i.test(text),
      containsMention: /@/i.test(text),
      wordCount: text.split(/\s+/).filter(Boolean).length,
      stats,
    };
    return base;
  } catch (error) {
    console.warn("Unable to normalize post", error);
    return null;
  }
}

function extractElements(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.elements)) return data.elements;
  if (Array.isArray(data.posts)) return data.posts;
  return [];
}

function extractText(payload = {}) {
  if (typeof payload.text === "string") {
    return payload.text.trim();
  }
  if (payload.text?.text) {
    return String(payload.text.text).trim();
  }
  const commentary =
    payload.specificContent?.["com.linkedin.ugc.ShareContent"]?.shareCommentary
      ?.text;
  if (typeof commentary === "string") {
    return commentary.trim();
  }
  return "";
}

function extractHashtags(payload = {}) {
  const tags = new Set();
  const contentTags = payload.content?.hashtags || payload.hashtags || [];
  contentTags.forEach((tag) => {
    if (typeof tag === "string") tags.add(tag.toLowerCase());
  });

  const body = extractText(payload);
  (body.match(/#[\w-]+/g) || []).forEach((tag) => {
    tags.add(tag.replace("#", "").toLowerCase());
  });

  return Array.from(tags);
}

function extractMediaType(payload = {}) {
  return (
    payload.mediaType ||
    payload.content?.media?.[0]?.mediaType ||
    payload.content?.mediaCategory ||
    payload.specificContent?.["com.linkedin.ugc.ShareContent"]?.shareMediaCategory ||
    null
  );
}

function extractVisibility(payload = {}) {
  return (
    payload.visibility?.["com.linkedin.ugc.MemberNetworkVisibility"] ||
    payload.visibility ||
    "PUBLIC"
  );
}

function extractDate(payload = {}) {
  if (payload.createdAt instanceof Date) {
    return payload.createdAt;
  }

  const timestamp =
    payload.createdAt?.time ||
    payload.createdAt ||
    payload.lastModified?.time ||
    payload.publishedAt;

  if (typeof timestamp === "number") {
    return new Date(timestamp > 1e12 ? timestamp : timestamp * 1000);
  }
  if (typeof timestamp === "string") {
    return new Date(timestamp);
  }
  return null;
}

function extractStats(payload = {}) {
  const stats =
    payload.stats ||
    payload.interactionStats ||
    payload.metrics ||
    payload.socialSummary ||
    {};

  const likes =
    stats.likes ??
    stats.reactions ??
    stats.likesCount ??
    stats.applauseCount ??
    payload.likes ??
    0;
  const comments =
    stats.comments ??
    stats.commentsCount ??
    stats.totalComments ??
    payload.comments ??
    0;
  const shares =
    stats.shares ?? stats.shareCount ?? stats.reshares ?? payload.shares ?? 0;
  const clicks =
    stats.clicks ??
    stats.clickThroughs ??
    stats.clickCount ??
    payload.clicks ??
    0;
  const impressions =
    stats.impressions ??
    stats.impressionsCount ??
    stats.views ??
    payload.impressions ??
    0;

  const totalInteractions =
    Number(likes || 0) +
    Number(comments || 0) +
    Number(shares || 0) +
    Number(clicks || 0);
  const engagementRate =
    impressions > 0 ? +(totalInteractions / impressions).toFixed(4) : 0;

  return {
    likes: Number(likes || 0),
    comments: Number(comments || 0),
    shares: Number(shares || 0),
    clicks: Number(clicks || 0),
    impressions: Number(impressions || 0),
    totalInteractions,
    engagementRate,
  };
}

function categorizePost(post, categoryRules = DEFAULT_CATEGORY_RULES) {
  const categories = [];
  const text = (post.text || "").toLowerCase();

  Object.entries(categoryRules).forEach(([category, keywords]) => {
    const match = keywords.some((keyword) => {
      const cleaned = keyword.trim().toLowerCase();
      if (!cleaned) return false;
      if (text.includes(cleaned)) return true;
      return post.hashtags.some((tag) => tag.includes(cleaned));
    });
    if (match) categories.push(category);
  });

  if (!categories.length) categories.push("general");
  return categories;
}

function parseCategoryConfig(raw) {
  if (!raw.trim()) return DEFAULT_CATEGORY_RULES;
  try {
    const parsed = JSON.parse(raw);
    const normalized = {};
    Object.entries(parsed).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        normalized[key] = value.map((entry) => String(entry).toLowerCase());
      } else if (typeof value === "string") {
        normalized[key] = [value.toLowerCase()];
      }
    });
    return Object.keys(normalized).length ? normalized : DEFAULT_CATEGORY_RULES;
  } catch (error) {
    showAlert("Could not parse category JSON; falling back to defaults.", "error");
    return DEFAULT_CATEGORY_RULES;
  }
}

function normalizeCounts(counter, total) {
  if (!total) return {};
  const normalized = {};
  Object.entries(counter).forEach(([key, value]) => {
    normalized[key] = +(value / total).toFixed(2);
  });
  return normalized;
}

function takeTopEntries(counter, limit = 5) {
  return Object.fromEntries(
    Object.entries(counter)
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit),
  );
}

function clampNumber(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function clearAlerts() {
  alertsEl.innerHTML = "";
}

function showAlert(message, type = "info") {
  const alert = document.createElement("div");
  alert.className = `alert alert--${type}`;
  alert.textContent = message;
  alertsEl.appendChild(alert);
}

function formatDate(date) {
  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatWeekday(date) {
  return new Intl.DateTimeFormat("en", { weekday: "long" }).format(date);
}

function formatPercent(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "0%";
  return (value * 100).toFixed(1) + "%";
}
