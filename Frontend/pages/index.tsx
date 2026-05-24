import { useEffect } from "react";
import { useRouter } from "next/router";

export default function Index() {
  const router = useRouter();
  useEffect(() => { router.replace("/boardroom"); }, [router]);
  return (
    <div style={{ background: "#0a0a0b", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <p style={{ color: "#6b7280", fontFamily: "monospace", fontSize: 13 }}>Loading Boardroom AI…</p>
    </div>
  );
}
