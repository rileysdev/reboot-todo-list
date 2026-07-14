import { type FC } from "react";
import { Navigate, useParams } from "react-router-dom";
import { Board } from "../components/Board";

export const BoardPage: FC = () => {
  const { id } = useParams();
  if (!id) return <Navigate to="/" replace />;
  return <Board listId={id} />;
};
