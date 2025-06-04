import { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import StatusBar from "@/components/layout/StatusBar";
import { Channel, PaginatedChannelTable } from "@/features/slack/ChannelTable";
import { ChannelSettingsDrawer } from "@/features/slack/ChannelSettingsDrawer";
import { AnimatePresence, motion } from "framer-motion";
import { useLocation } from "wouter";

export default function SlackIntegration() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [settingsChannel, setSettingsChannel] = useState<Channel | null>(null);
  const [, navigate] = useLocation();
  const handleConnect = () => {
    setIsConnecting(true);
    setTimeout(() => {
      setIsConnecting(false);
    }, 2000);
  };

  const handleSelectChannel = (channel: string) => {
    if (selectedChannels.includes(channel)) {
      setSelectedChannels(selectedChannels.filter(c => c !== channel));
    } else {
      setSelectedChannels([...selectedChannels, channel]);
    }
  };

  const channels: Channel[] = [
    { name: "general", messages: "5,832", lastSync: "10 minutes ago", status: "Active", frequency: "60" },
    { name: "engineering", messages: "3,451", lastSync: "1 hour ago", status: "Active", frequency: "30" },
    { name: "random", messages: "1,102", lastSync: "Yesterday", status: "Paused", frequency: "1440" },
    { name: "design", messages: "2,220", lastSync: "2 hours ago", status: "Active", frequency: "60" },
    { name: "marketing", messages: "800", lastSync: "3 days ago", status: "Archived", frequency: "720" },
    { name: "support", messages: "4,500", lastSync: "5 minutes ago", status: "Active", frequency: "30" },
    { name: "support", messages: "4,500", lastSync: "5 minutes ago", status: "Active", frequency: "10" },
    { name: "support", messages: "4,200", lastSync: "5 minutes ago", status: "Active", frequency: "30" },
    { name: "support", messages: "4,500", lastSync: "5 minutes ago", status: "Active", frequency: "30" },
    { name: "support", messages: "4,300", lastSync: "5 minutes ago", status: "Active", frequency: "30" },
    { name: "support", messages: "2,500", lastSync: "5 minutes ago", status: "Active", frequency: "30" },
    // …you can list 10, 20, 100 channels; pagination is automatic…
  ];

  const handleSave = (values: Record<string, string | boolean>) => {
    // Implement save logic here, e.g., update channel settings or make API call
    setSettingsChannel(null);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Slack Integration" onToggleSidebar={() => setSidebarOpen(s => !s)} />

        <main className="flex-1 overflow-y-auto p-6 bg-background-dark">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 overflow-hidden">
              <div className="lg:col-span-2">
 <PaginatedChannelTable
                  allChannels={channels}
                  onSettingsClick={setSettingsChannel}
                  onRefresh={() => {
                    // re-fetch or refresh logic here
                    console.log("Parent triggered refresh. Re-fetch channels…");
                  }}
                  // pageSize={8}  // <— optional override of items per page
                />
              </div>

              <AnimatePresence initial={false}>
                {settingsChannel && (
                  <div className="lg:col-span-1">
                    <ChannelSettingsDrawer
                      channelName={settingsChannel.name}
                      isOpen={settingsChannel !== null}
                      onClose={() => setSettingsChannel(null)}
                      onSave={handleSave}
                    />
                    {/* <ChannelSettingsDrawer
                      key={settingsChannel.name}
                      channel={settingsChannel}
                      onClose={() => setSettingsChannel(null)}
                    /> */}
                  </div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </main>
        <StatusBar />
      </div>
    </div>
  );
}
