import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import StatusBar from "@/components/layout/StatusBar";
import { motion } from "framer-motion";
import { AddSourceSection } from "./AddSourceSection";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";

export default function SlackAddSourcePage() {
  const [, navigate] = useLocation();
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Slack Integration – Add Source" onToggleSidebar={function (): void {
                  throw new Error("Function not implemented.");
              } } />
        <main className="flex-1 overflow-y-auto p-6 bg-background-dark">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <AddSourceSection />
                <div className="mt-6 flex justify-start space-x-3">
                    <Button
                        variant="outline"
                        onClick={() => window.history.back()}
                    >
                        Cancel
                    </Button>
                    <Button
                        // onClick={() => onSave(formValues)}
                    >
                        Add Channel
                    </Button>
                </div>
            </motion.div>
        </main>
        <StatusBar />
      </div>
    </div>
  );
}
