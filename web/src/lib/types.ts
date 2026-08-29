export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface Document {
  id: string;
  filename: string;
  status: DocumentStatus;
  chunk_count: number;
}

export interface Source {
  structure_path: string;
  page_number: number;
  document_id: string;
  chunk_id: string;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
  found: boolean;
}
