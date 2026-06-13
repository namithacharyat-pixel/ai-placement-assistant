import type { TopicCategory } from "@/lib/types/company";
import { TOPIC_CATEGORY_LABELS, TOPIC_CATEGORY_ORDER } from "@/lib/types/company";
import { getCategoryTopics } from "@/lib/companyUtils";
import type { Company } from "@/lib/types/company";

type Props = {
  company: Company;
  category: TopicCategory | "";
  topic: string;
  onCategoryChange: (category: TopicCategory | "") => void;
  onTopicChange: (topic: string) => void;
};

export function TopicSelector({ company, category, topic, onCategoryChange, onTopicChange }: Props) {
  const topics = category ? getCategoryTopics(company, category) : [];

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <label className="space-y-1.5">
        <span className="text-sm font-medium">Category</span>
        <select
          value={category}
          onChange={(e) => {
            onCategoryChange(e.target.value as TopicCategory | "");
            onTopicChange("");
          }}
          className="w-full h-10 rounded-lg border bg-background px-3 text-sm"
        >
          <option value="">Select category</option>
          {TOPIC_CATEGORY_ORDER.map((cat) => (
            <option key={cat} value={cat}>
              {TOPIC_CATEGORY_LABELS[cat]}
            </option>
          ))}
        </select>
      </label>

      <label className="space-y-1.5">
        <span className="text-sm font-medium">Topic</span>
        <select
          value={topic}
          onChange={(e) => onTopicChange(e.target.value)}
          disabled={!category}
          className="w-full h-10 rounded-lg border bg-background px-3 text-sm disabled:opacity-50"
        >
          <option value="">Select topic</option>
          {topics.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>

      {category && topics.length === 0 && (
        <p className="md:col-span-2 text-sm text-muted-foreground">
          No topics in this category yet. Analyze a JD for this company first.
        </p>
      )}
    </div>
  );
}
