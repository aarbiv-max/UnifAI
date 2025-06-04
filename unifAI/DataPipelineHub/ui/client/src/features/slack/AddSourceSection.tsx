import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { FaSearch } from "react-icons/fa";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";

export function AddSourceSection() {
  const [selectedChannels, setSelected] = useState<string[]>([]);
  const handleSelectChannel = (ch: string) =>
    setSelected(prev => prev.includes(ch) ? prev.filter(x=>x!==ch) : [...prev,ch]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className="bg-background-card shadow-card border-gray-800">
        <CardContent className="p-6">
          <h3 className="text-lg font-semibold mb-4">Channel Selection</h3>
                      <div className="space-y-6">
                        <div>
                          <Label htmlFor="channel-search" className="text-sm">
                            Search Channels
                          </Label>
                          <div className="relative mt-1">
                            <Input
                              id="channel-search"
                              placeholder="Search channels..."
                              className="pr-10 bg-background-dark"
                            />
                            <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                              <FaSearch className="text-gray-400" />
                            </div>
                          </div>
                        </div>

                        <div className="border border-gray-800 rounded-md h-64 overflow-y-auto bg-background-dark">
                          <div className="p-3 border-b border-gray-800 flex items-center justify-between hover:bg-background-surface cursor-pointer" onClick={() => handleSelectChannel('general')}>
                            <div className="flex items-center">
                              <span className="text-gray-400 mr-2">#</span>
                              <span>general</span>
                              <Badge className="ml-2 bg-secondary bg-opacity-20 text-secondary">
                                High Activity
                              </Badge>
                            </div>
                            <Switch checked={selectedChannels.includes('general')} onCheckedChange={() => handleSelectChannel('general')} />
                          </div>
                          <div className="p-3 border-b border-gray-800 flex items-center justify-between hover:bg-background-surface cursor-pointer" onClick={() => handleSelectChannel('engineering')}>
                            <div className="flex items-center">
                              <span className="text-gray-400 mr-2">#</span>
                              <span>engineering</span>
                            </div>
                            <Switch checked={selectedChannels.includes('engineering')} onCheckedChange={() => handleSelectChannel('engineering')} />
                          </div>
                          <div className="p-3 border-b border-gray-800 flex items-center justify-between hover:bg-background-surface cursor-pointer" onClick={() => handleSelectChannel('product')}>
                            <div className="flex items-center">
                              <span className="text-gray-400 mr-2">#</span>
                              <span>product</span>
                            </div>
                            <Switch checked={selectedChannels.includes('product')} onCheckedChange={() => handleSelectChannel('product')} />
                          </div>
                          <div className="p-3 border-b border-gray-800 flex items-center justify-between hover:bg-background-surface cursor-pointer" onClick={() => handleSelectChannel('design')}>
                            <div className="flex items-center">
                              <span className="text-gray-400 mr-2">#</span>
                              <span>design</span>
                            </div>
                            <Switch checked={selectedChannels.includes('design')} onCheckedChange={() => handleSelectChannel('design')} />
                          </div>
                          <div className="p-3 border-b border-gray-800 flex items-center justify-between hover:bg-background-surface cursor-pointer" onClick={() => handleSelectChannel('random')}>
                            <div className="flex items-center">
                              <span className="text-gray-400 mr-2">#</span>
                              <span>random</span>
                            </div>
                            <Switch checked={selectedChannels.includes('random')} onCheckedChange={() => handleSelectChannel('random')} />
                          </div>
                          <div className="p-3 border-b border-gray-800 flex items-center justify-between hover:bg-background-surface cursor-pointer" onClick={() => handleSelectChannel('announcements')}>
                            <div className="flex items-center">
                              <span className="text-gray-400 mr-2">#</span>
                              <span>announcements</span>
                            </div>
                            <Switch checked={selectedChannels.includes('announcements')} onCheckedChange={() => handleSelectChannel('announcements')} />
                          </div>
                          <div className="p-3 flex items-center justify-between hover:bg-background-surface cursor-pointer" onClick={() => handleSelectChannel('help')}>
                            <div className="flex items-center">
                              <span className="text-gray-400 mr-2">#</span>
                              <span>help</span>
                            </div>
                            <Switch checked={selectedChannels.includes('help')} onCheckedChange={() => handleSelectChannel('help')} />
                          </div>
                        </div>

                        <div className="flex justify-between items-center">
                          <span className="text-sm">
                            {selectedChannels.length} channels selected
                          </span>
                          <Button variant="outline" size="sm">
                            Select All
                          </Button>
                        </div>

                        <div>
                          <Label htmlFor="date-range" className="text-sm">
                            Date Range
                          </Label>
                          <Select defaultValue="30d">
                            <SelectTrigger
                              id="date-range"
                              className="mt-1 bg-background-dark"
                            >
                              <SelectValue placeholder="Select date range" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="7d">Last 7 days</SelectItem>
                              <SelectItem value="30d">Last 30 days</SelectItem>
                              <SelectItem value="90d">Last 90 days</SelectItem>
                              <SelectItem value="180d">Last 6 months</SelectItem>
                              <SelectItem value="365d">Last year</SelectItem>
                              <SelectItem value="all">All time</SelectItem>
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-gray-400 mt-1">
                            How far back to fetch messages
                          </p>
                        </div>

                        <div className="flex items-center justify-between pt-2">
                          <div>
                            <Label htmlFor="include-threads" className="text-base">
                              Include Threads
                            </Label>
                            <p className="text-xs text-gray-400 mt-1">
                              Process conversation threads
                            </p>
                          </div>
                          <Switch id="include-threads" defaultChecked />
                        </div>

                        <div className="relative">
                          <div className="absolute -left-3 -top-4">
                            <span className="text-xs px-2 py-0.5 rounded-full bg-primary text-white font-medium">
                              Soon
                            </span>
                          </div>
                          <div className="flex items-start justify-between opacity-50 cursor-not-allowed">
                            <div>
                              <Label htmlFor="include-files" className="text-base">
                                Process File Content
                              </Label>
                              <p className="text-xs text-gray-400 mt-1">
                                Extract text from shared files
                              </p>
                            </div>
                            <div className="flex items-center space-x-2 pt-1">
                              <Switch id="include-files" disabled />
                            </div>
                          </div>
                        </div>
                      </div>
        </CardContent>
      </Card>
    </div>
  );
}
