import React from "react";
import ReactDOM from "react-dom/client";
import {
  ExternalLink,
  Globe2,
  Loader2,
  Newspaper,
  RefreshCw,
  Search,
  SlidersHorizontal,
} from "lucide-react";

import { ArticleDetails, FeedArticle, fetchArticle, fetchFeed } from "./api";
import "./styles.css";

const topicOptions = [
  "ai",
  "technology",
  "business",
  "middle east",
  "politics",
  "science",
  "health",
  "sports",
  "entertainment",
];

function App() {
  const [selectedTopics, setSelectedTopics] = React.useState<string[]>(["ai", "technology"]);
  const [languages, setLanguages] = React.useState<string[]>(["ar", "en"]);
  const [maxArticles, setMaxArticles] = React.useState(10);
  const [feed, setFeed] = React.useState<FeedArticle[]>([]);
  const [selectedArticle, setSelectedArticle] = React.useState<FeedArticle | null>(null);
  const [articleDetails, setArticleDetails] = React.useState<ArticleDetails | null>(null);
  const [isLoadingFeed, setIsLoadingFeed] = React.useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  async function loadFeed() {
    setIsLoadingFeed(true);
    setErrorMessage(null);

    try {
      const articles = await fetchFeed({
        topics: selectedTopics,
        languages,
        max_articles: maxArticles,
      });
      setFeed(articles);
      setSelectedArticle(articles[0] ?? null);
      setArticleDetails(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setIsLoadingFeed(false);
    }
  }

  async function selectArticle(article: FeedArticle) {
    setSelectedArticle(article);
    setArticleDetails(null);
    setIsLoadingDetails(true);

    try {
      const details = await fetchArticle(article.id);
      setArticleDetails(details);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load details");
    } finally {
      setIsLoadingDetails(false);
    }
  }

  function toggleTopic(topic: string) {
    if (selectedTopics.includes(topic)) {
      setSelectedTopics(selectedTopics.filter((selectedTopic) => selectedTopic !== topic));
      return;
    }

    setSelectedTopics([...selectedTopics, topic]);
  }

  function toggleLanguage(language: string) {
    if (languages.includes(language)) {
      setLanguages(languages.filter((selectedLanguage) => selectedLanguage !== language));
      return;
    }

    setLanguages([...languages, language]);
  }

  return (
    <main className="app-shell">
      <section className="preferences-panel" aria-label="Preferences">
        <div className="panel-heading">
          <SlidersHorizontal size={18} />
          <h1>News Agent</h1>
        </div>

        <div className="control-group">
          <h2>Topics</h2>
          <div className="topic-grid">
            {topicOptions.map((topic) => (
              <button
                className={selectedTopics.includes(topic) ? "chip selected" : "chip"}
                key={topic}
                onClick={() => toggleTopic(topic)}
                type="button"
              >
                {topic}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <h2>Languages</h2>
          <label className="check-row">
            <input
              checked={languages.includes("ar")}
              onChange={() => toggleLanguage("ar")}
              type="checkbox"
            />
            Arabic
          </label>
          <label className="check-row">
            <input
              checked={languages.includes("en")}
              onChange={() => toggleLanguage("en")}
              type="checkbox"
            />
            English
          </label>
        </div>

        <div className="control-group">
          <h2>Articles</h2>
          <input
            className="range"
            max={20}
            min={1}
            onChange={(event) => setMaxArticles(Number(event.target.value))}
            type="range"
            value={maxArticles}
          />
          <div className="range-value">{maxArticles} ranked articles</div>
        </div>

        <button className="primary-action" disabled={isLoadingFeed} onClick={loadFeed} type="button">
          {isLoadingFeed ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
          Rank feed
        </button>

        {errorMessage && <p className="error-message">{errorMessage}</p>}
      </section>

      <section className="feed-panel" aria-label="Personalized feed">
        <div className="section-title">
          <Newspaper size={20} />
          <h2>Feed</h2>
          <button className="icon-button" disabled={isLoadingFeed} onClick={loadFeed} type="button">
            <RefreshCw size={17} />
          </button>
        </div>

        {feed.length === 0 && (
          <div className="empty-feed">
            <Globe2 size={28} />
            <p>Select preferences and rank your saved articles.</p>
          </div>
        )}

        <div className="feed-list">
          {feed.map((article) => (
            <button
              className={selectedArticle?.id === article.id ? "article-row active" : "article-row"}
              key={article.id}
              onClick={() => selectArticle(article)}
              type="button"
            >
              <div className="article-row-top">
                <span>{article.category ?? "other"}</span>
                <strong>{Math.round(article.score * 100)}%</strong>
              </div>
              <h3>{article.title}</h3>
              <p>{article.summary ?? "No summary saved yet."}</p>
              <div className="meta-line">
                {article.source} · {article.language ?? "unknown"}
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="details-panel" aria-label="Article details">
        {!selectedArticle && (
          <div className="empty-details">
            <Newspaper size={30} />
            <p>Choose an article to inspect its summary, ranking, and original link.</p>
          </div>
        )}

        {selectedArticle && (
          <ArticleDetailsView
            details={articleDetails}
            fallbackArticle={selectedArticle}
            isLoading={isLoadingDetails}
          />
        )}
      </section>
    </main>
  );
}

function ArticleDetailsView({
  details,
  fallbackArticle,
  isLoading,
}: {
  details: ArticleDetails | null;
  fallbackArticle: FeedArticle;
  isLoading: boolean;
}) {
  const article = details ?? fallbackArticle;
  const keyPoints = details?.key_points ?? [];
  const topics = article.topics ?? [];

  return (
    <div className="details-content">
      <div className="details-meta">
        <span>{article.source}</span>
        <span>{article.language ?? "unknown"}</span>
        <span>{article.category ?? "other"}</span>
      </div>

      <h2>{article.title}</h2>

      {isLoading && (
        <div className="loading-line">
          <Loader2 className="spin" size={16} />
          Loading details
        </div>
      )}

      <p className="summary-text">{article.summary ?? "No summary saved yet."}</p>

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

      <div className="detail-block">
        <h3>Ranking</h3>
        <div className="score-grid">
          <Score label="Final" value={fallbackArticle.score} />
          <Score label="AI" value={fallbackArticle.ai_relevance} />
          <Score label="Fresh" value={fallbackArticle.freshness_score} />
          <Score label="Topic" value={fallbackArticle.topic_match_score} />
        </div>
        <p className="reason">{fallbackArticle.reason}</p>
      </div>

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

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="score-item">
      <span>{label}</span>
      <strong>{Math.round(value * 100)}%</strong>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
