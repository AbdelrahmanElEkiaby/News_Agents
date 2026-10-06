import React from "react";
import ReactDOM from "react-dom/client";
import {
  CalendarClock,
  Database,
  ExternalLink,
  Globe2,
  LayoutGrid,
  Loader2,
  LogOut,
  Newspaper,
  Plus,
  Power,
  PowerOff,
  RefreshCw,
  Search,
  Sparkles,
  Tags,
  Trash2,
} from "lucide-react";

import {
  ArticleDetails,
  ArticleFetchResult,
  DiscoveredFeed,
  Source,
  User,
  clearToken,
  createSource,
  deleteSource,
  discoverSource,
  fetchArticles,
  fetchCurrentUser,
  fetchSources,
  fetchUserSources,
  generateArticleSummary,
  getStoredToken,
  scanSources,
  subscribeToSource,
  unsubscribeFromSource,
  updateSource,
} from "./api";
import { AuthPage } from "./AuthPage";
import "./styles.css";

function App() {
  const [activeView, setActiveView] = React.useState<"feed" | "sources">("sources");
  const [articles, setArticles] = React.useState<ArticleDetails[]>([]);
  const [selectedArticle, setSelectedArticle] = React.useState<ArticleDetails | null>(null);
  const [selectedCategory, setSelectedCategory] = React.useState<string | null>(null);
  const [selectedTopic, setSelectedTopic] = React.useState<string | null>(null);
  const [publishedFrom, setPublishedFrom] = React.useState("");
  const [publishedUntil, setPublishedUntil] = React.useState("");
  const [isLoadingArticles, setIsLoadingArticles] = React.useState(false);
  const [summarizingArticleId, setSummarizingArticleId] = React.useState<number | null>(null);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [feedMessage, setFeedMessage] = React.useState<string | null>(null);
  const [currentUser, setCurrentUser] = React.useState<User | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = React.useState(true);

  React.useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      if (!getStoredToken()) {
        setIsCheckingAuth(false);
        return;
      }

      try {
        const user = await fetchCurrentUser();

        if (isMounted) {
          setCurrentUser(user);
        }
      } catch {
        clearToken();
      } finally {
        if (isMounted) {
          setIsCheckingAuth(false);
        }
      }
    }

    function handleUnauthorized() {
      if (isMounted) {
        setCurrentUser(null);
      }
    }

    window.addEventListener("auth:unauthorized", handleUnauthorized);
    restoreSession();

    return () => {
      isMounted = false;
      window.removeEventListener("auth:unauthorized", handleUnauthorized);
    };
  }, []);

  const loadArticles = React.useCallback(async () => {
    setIsLoadingArticles(true);
    setErrorMessage(null);

    try {
      const loadedArticles = await fetchArticles();
      setArticles(loadedArticles);
      setSelectedArticle((currentArticle) => {
        if (currentArticle) {
          return (
            loadedArticles.find((article) => article.id === currentArticle.id) ??
            loadedArticles[0] ??
            null
          );
        }

        return loadedArticles[0] ?? null;
      });
      return loadedArticles.length;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load articles");
      return 0;
    } finally {
      setIsLoadingArticles(false);
    }
  }, []);

  React.useEffect(() => {
    if (currentUser) {
      loadArticles();
    }
  }, [currentUser, loadArticles]);

  const categoryCounts = React.useMemo(
    () => countValues(articles.flatMap((article) => (article.category ? [article.category] : []))),
    [articles],
  );
  const topicCounts = React.useMemo(
    () => countValues(articles.flatMap((article) => article.topics ?? [])),
    [articles],
  );
  const filteredArticles = React.useMemo(() => {
    const fromTimestamp = publishedFrom ? new Date(publishedFrom).getTime() : null;
    const untilTimestamp = publishedUntil
      ? new Date(publishedUntil).getTime() + 60_000 - 1
      : null;

    return articles.filter((article) => {
      const matchesCategory = !selectedCategory || article.category === selectedCategory;
      const matchesTopic = !selectedTopic || article.topics?.includes(selectedTopic);
      const publishedTimestamp = new Date(article.published_at ?? article.created_at).getTime();
      const matchesFrom = fromTimestamp === null || publishedTimestamp >= fromTimestamp;
      const matchesUntil = untilTimestamp === null || publishedTimestamp <= untilTimestamp;

      return matchesCategory && matchesTopic && matchesFrom && matchesUntil;
    });
  }, [articles, publishedFrom, publishedUntil, selectedCategory, selectedTopic]);

  React.useEffect(() => {
    if (selectedCategory && !categoryCounts.some(([value]) => value === selectedCategory)) {
      setSelectedCategory(null);
    }

    if (selectedTopic && !topicCounts.some(([value]) => value === selectedTopic)) {
      setSelectedTopic(null);
    }
  }, [categoryCounts, selectedCategory, selectedTopic, topicCounts]);

  React.useEffect(() => {
    if (
      selectedArticle &&
      !filteredArticles.some((article) => article.id === selectedArticle.id)
    ) {
      setSelectedArticle(filteredArticles[0] ?? null);
    }
  }, [filteredArticles, selectedArticle]);

  function logout() {
    clearToken();
    setCurrentUser(null);
    setArticles([]);
    setSelectedArticle(null);
    setSelectedCategory(null);
    setSelectedTopic(null);
    setPublishedFrom("");
    setPublishedUntil("");
  }

  async function handleScanComplete(result: ArticleFetchResult) {
    const savedArticleCount = await loadArticles();
    setFeedMessage(
      result.saved > 0
        ? `Added ${result.saved} new article${result.saved === 1 ? "" : "s"} and loaded your feed.`
        : `No new articles were published. Showing ${savedArticleCount} saved article${savedArticleCount === 1 ? "" : "s"}.`,
    );
    setActiveView("feed");
  }

  async function handleGenerateSummary(article: ArticleDetails) {
    if (summarizingArticleId !== null) {
      return;
    }

    setSummarizingArticleId(article.id);
    setErrorMessage(null);

    try {
      const summarizedArticle = await generateArticleSummary(article.id);
      setArticles((currentArticles) =>
        currentArticles.map((currentArticle) =>
          currentArticle.id === summarizedArticle.id ? summarizedArticle : currentArticle,
        ),
      );
      setSelectedArticle((currentArticle) =>
        currentArticle?.id === summarizedArticle.id ? summarizedArticle : currentArticle,
      );
    } catch (error) {
      await loadArticles();
      setErrorMessage(error instanceof Error ? error.message : "Could not generate summary");
    } finally {
      setSummarizingArticleId(null);
    }
  }

  if (isCheckingAuth) {
    return (
      <main className="auth-loading">
        <Loader2 className="spin" size={24} />
        Checking your session
      </main>
    );
  }

  if (currentUser === null) {
    return <AuthPage onAuthenticated={setCurrentUser} />;
  }

  return (
    <main className="app-shell">
      <section className="preferences-panel" aria-label="Preferences">
        <div className="panel-heading">
          <Newspaper size={18} />
          <h1>News Agent</h1>
        </div>

        <div className="view-tabs">
          <button
            className={activeView === "feed" ? "tab-button active" : "tab-button"}
            onClick={() => setActiveView("feed")}
            type="button"
          >
            <Newspaper size={16} />
            Feed
          </button>
          <button
            className={activeView === "sources" ? "tab-button active" : "tab-button"}
            onClick={() => setActiveView("sources")}
            type="button"
          >
            <Database size={16} />
            Sources
          </button>
        </div>

        <div className="account-card">
          <div>
            <strong>{currentUser.name}</strong>
            <span>{currentUser.email}</span>
          </div>
          <button aria-label="Logout" onClick={logout} title="Logout" type="button">
            <LogOut size={16} />
          </button>
        </div>

        {activeView === "feed" && (
          <>
            <FilterGroup
              icon={<LayoutGrid size={15} />}
              label="Categories"
              options={categoryCounts}
              selected={selectedCategory}
              onSelect={setSelectedCategory}
            />
            <FilterGroup
              icon={<Tags size={15} />}
              label="Topics"
              options={topicCounts}
              selected={selectedTopic}
              onSelect={setSelectedTopic}
            />
            <DateTimeFilter
              from={publishedFrom}
              onFromChange={(value) => {
                setPublishedFrom(value);
                if (publishedUntil && value > publishedUntil) {
                  setPublishedUntil(value);
                }
              }}
              onUntilChange={(value) => {
                setPublishedUntil(value);
                if (publishedFrom && value < publishedFrom) {
                  setPublishedFrom(value);
                }
              }}
              until={publishedUntil}
            />

            {(selectedCategory || selectedTopic || publishedFrom || publishedUntil) && (
              <button
                className="clear-filters"
                onClick={() => {
                  setSelectedCategory(null);
                  setSelectedTopic(null);
                  setPublishedFrom("");
                  setPublishedUntil("");
                }}
                type="button"
              >
                Show all articles
              </button>
            )}
          </>
        )}

        {errorMessage && <p className="error-message">{errorMessage}</p>}
      </section>

      {activeView === "feed" && (
        <>
          <section className="feed-panel" aria-label="Personalized feed">
            <div className="section-title">
              <Newspaper size={20} />
              <div className="section-title-copy">
                <h2>News</h2>
                <span>{filteredArticles.length} articles</span>
              </div>
              <button
                aria-label="Reload saved articles"
                className="icon-button"
                disabled={isLoadingArticles}
                onClick={loadArticles}
                title="Reload saved articles"
                type="button"
              >
                {isLoadingArticles ? (
                  <Loader2 className="spin" size={17} />
                ) : (
                  <RefreshCw size={17} />
                )}
              </button>
            </div>

            {feedMessage && <p className="feed-message">{feedMessage}</p>}

            {articles.length === 0 && !isLoadingArticles && (
              <div className="empty-feed">
                <Globe2 size={28} />
                <p>Add and subscribe to sources, then scan them to build your feed.</p>
                <button className="secondary-action" onClick={() => setActiveView("sources")}>
                  Manage sources
                </button>
              </div>
            )}

            {articles.length > 0 && filteredArticles.length === 0 && (
              <div className="empty-feed">
                <Search size={28} />
                <p>No saved articles match these filters.</p>
              </div>
            )}

            <div className="feed-list">
              {filteredArticles.map((article) => (
                <button
                  className={selectedArticle?.id === article.id ? "article-row active" : "article-row"}
                  key={article.id}
                  onClick={() => setSelectedArticle(article)}
                  type="button"
                >
                  <div className="article-row-top">
                    <span>{formatLabel(article.category ?? "unclassified")}</span>
                    <strong>{formatDate(article.published_at)}</strong>
                  </div>
                  <h3>{article.title}</h3>
                  <p>{getArticlePreview(article)}</p>
                  <div className="meta-line">
                    {article.source} - {article.language ?? "unknown"}
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section className="details-panel" aria-label="Article details">
            {!selectedArticle && (
              <div className="empty-details">
                <Newspaper size={30} />
                <p>Choose an article to read its saved content.</p>
              </div>
            )}

            {selectedArticle && (
              <ArticleDetailsView
                article={selectedArticle}
                activeSummaryRequestId={summarizingArticleId}
                onGenerateSummary={handleGenerateSummary}
              />
            )}
          </section>
        </>
      )}

      {activeView === "sources" && <SourceManagementView onScanComplete={handleScanComplete} />}
    </main>
  );
}

function FilterGroup({
  icon,
  label,
  options,
  selected,
  onSelect,
}: {
  icon: React.ReactNode;
  label: string;
  options: Array<[string, number]>;
  selected: string | null;
  onSelect: (value: string | null) => void;
}) {
  if (options.length === 0) {
    return null;
  }

  return (
    <div className="control-group">
      <h2>
        {icon}
        {label}
      </h2>
      <div className="filter-grid">
        {options.map(([value, count]) => (
          <button
            className={selected === value ? "filter-card selected" : "filter-card"}
            key={value}
            onClick={() => onSelect(selected === value ? null : value)}
            type="button"
          >
            <span>{formatLabel(value)}</span>
            <strong>{count}</strong>
          </button>
        ))}
      </div>
    </div>
  );
}

function DateTimeFilter({
  from,
  until,
  onFromChange,
  onUntilChange,
}: {
  from: string;
  until: string;
  onFromChange: (value: string) => void;
  onUntilChange: (value: string) => void;
}) {
  return (
    <div className="control-group">
      <h2>
        <CalendarClock size={15} />
        Published date & time
      </h2>
      <div className="date-time-grid">
        <label>
          <span>From</span>
          <input
            max={until || undefined}
            onChange={(event) => onFromChange(event.target.value)}
            type="datetime-local"
            value={from}
          />
        </label>
        <label>
          <span>Until</span>
          <input
            min={from || undefined}
            onChange={(event) => onUntilChange(event.target.value)}
            type="datetime-local"
            value={until}
          />
        </label>
      </div>
    </div>
  );
}

function countValues(values: string[]): Array<[string, number]> {
  const counts = new Map<string, number>();

  values.forEach((value) => counts.set(value, (counts.get(value) ?? 0) + 1));
  return [...counts.entries()].sort(([first], [second]) => first.localeCompare(second));
}

function formatLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character: string) => character.toUpperCase());
}

function getArticlePreview(article: ArticleDetails) {
  const preview = article.summary || article.description || article.content;
  if (!preview) {
    return "Open the original article to read more.";
  }

  return preview.length > 180 ? `${preview.slice(0, 177)}...` : preview;
}

function SourceManagementView({
  onScanComplete,
}: {
  onScanComplete: (result: ArticleFetchResult) => Promise<void>;
}) {
  const [sources, setSources] = React.useState<Source[]>([]);
  const [websiteUrl, setWebsiteUrl] = React.useState("");
  const [feedUrl, setFeedUrl] = React.useState("");
  const [sourceName, setSourceName] = React.useState("");
  const [language, setLanguage] = React.useState("en");
  const [discoveredFeeds, setDiscoveredFeeds] = React.useState<DiscoveredFeed[]>([]);
  const [selectedFeedUrl, setSelectedFeedUrl] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isScanning, setIsScanning] = React.useState(false);
  const [subscribedSourceIds, setSubscribedSourceIds] = React.useState<Set<number>>(new Set());

  React.useEffect(() => {
    loadSources();
  }, []);

  async function loadSources() {
    setIsLoading(true);
    setMessage(null);

    try {
      const [loadedSources, subscribedSources] = await Promise.all([
        fetchSources(),
        fetchUserSources(),
      ]);
      setSources(loadedSources);
      setSubscribedSourceIds(new Set(subscribedSources.map((source) => source.id)));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load sources");
    } finally {
      setIsLoading(false);
    }
  }

  async function addSource(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!websiteUrl.trim() && !feedUrl.trim()) {
      setMessage("Enter a website URL or a direct RSS/Atom feed URL.");
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      if (feedUrl.trim()) {
        await saveFeed(feedUrl.trim());
      } else if (discoveredFeeds.length > 0) {
        const selectedFeed = discoveredFeeds.find(
          (candidate) => candidate.feed_url === selectedFeedUrl,
        );

        if (!selectedFeed) {
          setMessage("Choose one of the discovered feeds.");
          return;
        }

        await saveFeed(selectedFeed.feed_url, selectedFeed.title);
      } else {
        const discovery = await discoverSource(websiteUrl);

        if (!discovery.feed_found || discovery.feeds.length === 0) {
          setMessage(discovery.message);
          return;
        }

        if (discovery.feeds.length > 1) {
          setDiscoveredFeeds(discovery.feeds);
          setSelectedFeedUrl(discovery.recommended_feed ?? discovery.feeds[0].feed_url);
          setMessage(`Found ${discovery.feeds.length} feeds. Choose one to add.`);
          return;
        }

        await saveFeed(discovery.feeds[0].feed_url, discovery.feeds[0].title);
      }

      resetSourceForm();
      await loadSources();
      setMessage("Source added successfully.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not add source");
    } finally {
      setIsLoading(false);
    }
  }

  async function scanSubscribedSources() {
    if (subscribedSourceIds.size === 0) {
      setMessage("Add or subscribe to at least one source before scanning.");
      return;
    }

    setIsScanning(true);
    setMessage(null);

    try {
      const result = await scanSources();
      await loadSources();
      await onScanComplete(result);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not scan sources");
    } finally {
      setIsScanning(false);
    }
  }

  async function saveFeed(selectedUrl: string, discoveredTitle?: string) {
    const source = await createSource({
      name: sourceName.trim() || discoveredTitle || getSourceName(websiteUrl || selectedUrl),
      website_url: websiteUrl.trim() || null,
      feed_url: selectedUrl,
      language,
      source_type: "rss",
    });

    await subscribeToSource(source.id);
  }

  function resetSourceForm() {
    setWebsiteUrl("");
    setFeedUrl("");
    setSourceName("");
    setDiscoveredFeeds([]);
    setSelectedFeedUrl("");
  }

  async function toggleSource(source: Source) {
    setIsLoading(true);
    setMessage(null);

    try {
      await updateSource(source.id, { is_active: !source.is_active });
      await loadSources();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update source");
    } finally {
      setIsLoading(false);
    }
  }

  async function removeSource(source: Source) {
    setIsLoading(true);
    setMessage(null);

    try {
      await deleteSource(source.id);
      await loadSources();
      setMessage("Source removed. Existing articles were kept.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not delete source");
    } finally {
      setIsLoading(false);
    }
  }

  async function toggleSubscription(source: Source) {
    setIsLoading(true);
    setMessage(null);

    try {
      let successMessage: string;

      if (subscribedSourceIds.has(source.id)) {
        await unsubscribeFromSource(source.id);
        successMessage = `Unsubscribed from ${source.name}.`;
      } else {
        await subscribeToSource(source.id);
        successMessage = `Subscribed to ${source.name}.`;
      }

      await loadSources();
      setMessage(successMessage);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update subscription");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="sources-panel" aria-label="Sources">
      <div className="section-title">
        <Database size={20} />
        <h2>Sources</h2>
        <button
          aria-label="Refresh sources"
          className="icon-button"
          disabled={isLoading}
          onClick={loadSources}
          title="Refresh sources"
          type="button"
        >
          {isLoading ? <Loader2 className="spin" size={17} /> : <RefreshCw size={17} />}
        </button>
      </div>

      <p className="source-help">
        Enter a website for automatic discovery. If the website blocks discovery, paste its
        direct RSS or Atom URL too. New sources are subscribed to your account.
      </p>

      <div className="scan-card">
        <div>
          <strong>Scan your subscribed sources</strong>
          <p>
            Fetch new articles and classify their categories and topics. Existing saved articles
            remain available when nothing new is published.
          </p>
        </div>
        <button
          className="primary-action compact-action"
          disabled={isScanning || isLoading || subscribedSourceIds.size === 0}
          onClick={scanSubscribedSources}
          type="button"
        >
          {isScanning ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
          {isScanning ? "Scanning..." : "Scan sources"}
        </button>
      </div>

      <form className="source-form" onSubmit={addSource}>
        <input
          onChange={(event) => {
            setWebsiteUrl(event.target.value);
            setDiscoveredFeeds([]);
            setSelectedFeedUrl("");
          }}
          placeholder="Website URL"
          type="url"
          value={websiteUrl}
        />
        <input
          onChange={(event) => {
            setFeedUrl(event.target.value);
            setDiscoveredFeeds([]);
            setSelectedFeedUrl("");
          }}
          placeholder="RSS/Atom URL (optional)"
          type="url"
          value={feedUrl}
        />
        <input
          onChange={(event) => setSourceName(event.target.value)}
          placeholder="Name"
          type="text"
          value={sourceName}
        />
        <select onChange={(event) => setLanguage(event.target.value)} value={language}>
          <option value="en">English</option>
          <option value="ar">Arabic</option>
        </select>
        <button className="primary-action compact-action" disabled={isLoading} type="submit">
          <Plus size={18} />
          {discoveredFeeds.length > 0
            ? "Add Selected"
            : feedUrl.trim()
              ? "Add Source"
              : "Discover"}
        </button>

        {discoveredFeeds.length > 1 && (
          <label className="feed-choice">
            <span>Choose a discovered feed</span>
            <select
              onChange={(event) => setSelectedFeedUrl(event.target.value)}
              value={selectedFeedUrl}
            >
              {discoveredFeeds.map((feed) => (
                <option key={feed.feed_url} value={feed.feed_url}>
                  {feed.title} ({feed.item_count} items)
                </option>
              ))}
            </select>
          </label>
        )}
      </form>

      {message && <p className="source-message">{message}</p>}

      <div className="source-list">
        {sources.map((source) => (
          <article className="source-row" key={source.id}>
            <div>
              <div className="source-row-title">
                <h3>{source.name}</h3>
                <span className={source.is_active ? "status active" : "status"}>
                  {source.is_active ? "Active" : "Disabled"}
                </span>
                {subscribedSourceIds.has(source.id) && (
                  <span className="status subscribed">Subscribed</span>
                )}
              </div>
              <p>
                {source.source_type.toUpperCase()} - {source.language}
              </p>
              {source.feed_url && <p className="source-url">{source.feed_url}</p>}
              <p>Last fetched: {formatDate(source.last_fetched_at)}</p>
              {source.last_error && <p className="source-error">{source.last_error}</p>}
            </div>

            <div className="source-actions">
              <button
                className="subscription-button"
                onClick={() => toggleSubscription(source)}
                type="button"
              >
                {subscribedSourceIds.has(source.id) ? "Unsubscribe" : "Subscribe"}
              </button>
              <button
                aria-label={source.is_active ? "Disable source" : "Enable source"}
                className="icon-button"
                onClick={() => toggleSource(source)}
                title={source.is_active ? "Disable source" : "Enable source"}
                type="button"
              >
                {source.is_active ? <PowerOff size={17} /> : <Power size={17} />}
              </button>
              <button
                aria-label="Delete source"
                className="icon-button"
                onClick={() => removeSource(source)}
                title="Remove source (keeps existing articles)"
                type="button"
              >
                <Trash2 size={17} />
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function formatDate(value: string | null) {
  if (!value) {
    return "Never";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getSourceName(url: string) {
  try {
    const normalizedUrl = url.startsWith("http") ? url : `https://${url}`;
    return new URL(normalizedUrl).hostname.replace("www.", "");
  } catch {
    return "New Source";
  }
}

function ArticleDetailsView({
  article,
  activeSummaryRequestId,
  onGenerateSummary,
}: {
  article: ArticleDetails;
  activeSummaryRequestId: number | null;
  onGenerateSummary: (article: ArticleDetails) => Promise<void>;
}) {
  const keyPoints = article.key_points ?? [];
  const topics = article.topics ?? [];
  const savedContent = article.summary || article.content || article.description;
  const classificationReady = Boolean(
    article.language && article.category && article.topics && article.importance,
  );
  const processingStartedAt = article.summary_requested_at
    ? new Date(article.summary_requested_at).getTime()
    : 0;
  const processingIsActive =
    article.summary_status === "processing" &&
    processingStartedAt > Date.now() - 5 * 60 * 1000;
  const isGeneratingThisArticle = activeSummaryRequestId === article.id;
  const summaryButtonDisabled =
    activeSummaryRequestId !== null || processingIsActive || !classificationReady;

  return (
    <div className="details-content">
      <div className="details-meta">
        <span>{article.source}</span>
        <span>{article.language ?? "unknown"}</span>
        <span>{formatLabel(article.category ?? "unclassified")}</span>
        {article.importance && <span>{formatLabel(article.importance)} importance</span>}
      </div>

      <h2>{article.title}</h2>

      <p className="article-date">{formatDate(article.published_at)}</p>

      {savedContent ? (
        <div className="detail-block">
          <h3>{article.summary ? "Saved Summary" : "Saved Content"}</h3>
          <p className="summary-text">{savedContent}</p>
        </div>
      ) : (
        <p className="summary-text">
          No extracted content is saved. Use the original article link below.
        </p>
      )}

      {!article.summary && (
        <div className="summary-action-card">
          <div>
            <strong>Need a shorter version?</strong>
            <p>
              A summary is generated once, saved, and reused for everyone viewing this article.
            </p>
          </div>
          <button
            className="primary-action compact-action"
            disabled={summaryButtonDisabled}
            onClick={() => onGenerateSummary(article)}
            type="button"
          >
            {isGeneratingThisArticle ? (
              <Loader2 className="spin" size={17} />
            ) : (
              <Sparkles size={17} />
            )}
            {isGeneratingThisArticle
              ? "Generating..."
              : processingIsActive
                ? "Summary in progress"
                : classificationReady
                  ? "Generate summary"
                  : "Waiting for classification"}
          </button>
        </div>
      )}

      {article.summary_generated_at && (
        <p className="summary-generated-at">
          Summary saved {formatDate(article.summary_generated_at)}
        </p>
      )}

      {keyPoints.length > 0 && (
        <div className="detail-block">
          <h3>Key Points</h3>
          <ul>
            {keyPoints.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </div>
      )}

      {topics.length > 0 && (
        <div className="topic-list">
          {topics.map((topic) => (
            <span key={topic}>{topic}</span>
          ))}
        </div>
      )}

      <a className="original-link" href={article.url} rel="noreferrer" target="_blank">
        <ExternalLink size={17} />
        Read original
      </a>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
