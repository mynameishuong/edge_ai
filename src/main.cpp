#include <algorithm>
#include <array>
#include <chrono>
#include <cctype>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#ifdef __linux__
#include <cerrno>
#include <cstring>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

// Feature contract v1: fixed 100 ms tumbling windows, eight float32 values.
constexpr size_t NF = 8;
constexpr uint64_t WINDOW_US = 100000;
using Features = std::array<float, NF>;
struct Frame { uint64_t us; uint32_t id; std::vector<uint8_t> data; };
struct Window { uint64_t start; size_t count; Features x; size_t unknown; };

class Extractor {
    uint64_t start_ = 0, last_ = 0;
    bool initialized_ = false;
    size_t count_ = 0, bytes_ = 0, comparisons_ = 0, iats_ = 0, unknown_ = 0;
    double sum_ = 0, sq_ = 0, flips_ = 0, iat_ = 0;
    std::map<uint32_t, size_t> counts_;
    std::map<uint32_t, Frame> previous_;
    const std::set<uint32_t>& whitelist_;
public:
    explicit Extractor(const std::set<uint32_t>& ids) : whitelist_(ids) {}
    Window finish() const {
        Features x{};
        if (count_) {
            double entropy = 0, mx = 0;
            for (auto [id, n] : counts_) {
                (void)id;
                double p = double(n) / count_;
                entropy -= p * std::log2(p); mx = std::max(mx, p);
            }
            double mean = bytes_ ? sum_ / bytes_ : 0;
            x = {float(count_ * 10.0), float(counts_.size()), float(entropy), float(mx),
                 float(mean), float(bytes_ ? std::sqrt(std::max(0.0, sq_/bytes_-mean*mean)) : 0),
                 float(comparisons_ ? flips_/comparisons_ : 0), float(iats_ ? iat_/iats_ : 0)};
        }
        return {start_, count_, x, unknown_};
    }
    void reset() {
        count_=bytes_=comparisons_=iats_=unknown_=0;
        sum_=sq_=flips_=iat_=0; counts_.clear(); previous_.clear();
    }
    template<class Emit> void advance(uint64_t us, Emit emit) {
        if (!initialized_) { start_ = us / WINDOW_US * WINDOW_US; initialized_ = true; }
        if (us < last_) throw std::runtime_error("timestamps must be nondecreasing");
        if (us - last_ > 3600000000ULL && last_ != 0)
            throw std::runtime_error("timestamp gap over one hour; split capture first");
        last_ = us;
        while (us >= start_ + WINDOW_US) {
            emit(finish()); start_ += WINDOW_US; reset();
        }
    }
    template<class Emit> void push(const Frame& f, Emit emit) {
        advance(f.us, emit);
        ++count_; ++counts_[f.id];
        if (!whitelist_.empty() && !whitelist_.count(f.id)) ++unknown_;
        for (auto b : f.data) { ++bytes_; sum_ += b; sq_ += double(b)*b; }
        auto it = previous_.find(f.id);
        if (it != previous_.end()) {
            iat_ += double(f.us-it->second.us)/1000; ++iats_;
            auto& prev = it->second.data;
            if (prev.size() == f.data.size() && !prev.empty()) {
                unsigned bits=0;
                for(size_t i=0;i<prev.size();++i) {
                    auto v = unsigned(prev[i]^f.data[i]);
                    while(v) { bits += v & 1U; v >>= 1U; }
                }
                flips_ += double(bits)/(prev.size()*8); ++comparisons_;
            }
        }
        previous_[f.id] = f;
    }
};

Frame parse_frame(const std::string& line) {
    std::istringstream ss(line); std::string t,id,dlc,data;
    if (!std::getline(ss,t,',') || !std::getline(ss,id,',') ||
        !std::getline(ss,dlc,',') || !std::getline(ss,data,','))
        throw std::runtime_error("invalid frame CSV row");
    if(t.empty() || !std::all_of(t.begin(),t.end(),[](unsigned char c){return std::isdigit(c);}))
        throw std::runtime_error("timestamp must be unsigned integer microseconds");
    if(id.empty() || !std::all_of(id.begin(),id.end(),[](unsigned char c){return std::isxdigit(c);}) ||
       !std::all_of(data.begin(),data.end(),[](unsigned char c){return std::isxdigit(c);}))
        throw std::runtime_error("invalid CAN ID/payload hex");
    size_t p=0; auto timestamp=std::stoull(t,&p);
    if(p!=t.size()) throw std::runtime_error("invalid timestamp");
    auto canid=std::stoul(id,&p,16);
    if(p!=id.size() || canid>0x7ff) throw std::runtime_error("v1 accepts standard 11-bit data frames only");
    auto n=std::stoul(dlc,&p);
    if(p!=dlc.size() || n>8 || data.size()!=2*n) throw std::runtime_error("DLC/payload mismatch");
    Frame f{timestamp, uint32_t(canid), {}};
    for(size_t i=0;i<n;++i) {
        auto b=std::stoul(data.substr(2*i,2),&p,16);
        if(p!=2) throw std::runtime_error("invalid payload hex");
        f.data.push_back(uint8_t(b));
    }
    return f;
}
template<class Emit> void read_csv(const std::string& path, Emit emit) {
    std::ifstream in(path); if(!in) throw std::runtime_error("cannot open CSV: "+path);
    std::string line; std::getline(in,line);
    if(line.find("timestamp_us,can_id_hex,dlc,data_hex")!=0) throw std::runtime_error("unexpected CSV header");
    size_t row=1;
    while(std::getline(in,line)) {
        ++row; if(!line.empty() && line.back()=='\r') line.pop_back();
        if(line.empty()) continue;
        try { emit(parse_frame(line)); }
        catch(const std::exception& e) { throw std::runtime_error("row "+std::to_string(row)+": "+e.what()); }
    }
    // Deliberately do not score the final incomplete window.
}
double correction(int n) {
    if(n<=1) return 0;
    if(n==2) return 1;
    return 2*(std::log(n-1.0)+0.5772156649015329)-2*(n-1.0)/n;
}
struct Node { int left,right,feature; double threshold; int samples; };
struct Forest {
    std::vector<std::vector<Node>> trees;
    int max_samples=0; double threshold=0;
    std::set<uint32_t> whitelist;
    explicit Forest(const std::string& path) {
        std::ifstream in(path); std::string magic;
        int nf,nt,nids; uint64_t window;
        if(!(in>>magic>>nf>>nt>>max_samples>>threshold>>window>>nids) ||
            magic!="AIVIDS_IFOREST_V1" || nf!=int(NF) || window!=WINDOW_US ||
            nt<1 || nt>1024 || max_samples<2 || max_samples>65536 || nids<1 || nids>2048 ||
            !std::isfinite(threshold) || threshold<0 || threshold>1)
            throw std::runtime_error("model header/schema invalid");
        for(int i=0;i<nids;++i) { unsigned id; if(!(in>>id) || id>0x7ff) throw std::runtime_error("invalid model ID"); whitelist.insert(id); }
        for(int i=0;i<nt;++i) {
            int count; if(!(in>>count) || count<1 || count>2*max_samples) throw std::runtime_error("invalid tree size");
            std::vector<Node> tree(count);
            for(int j=0;j<count;++j) {
                auto& n=tree[j];
                if(!(in>>n.left>>n.right>>n.feature>>n.threshold>>n.samples) ||
                   !std::isfinite(n.threshold) || n.samples<1 || n.samples>max_samples)
                    throw std::runtime_error("invalid model node");
                bool leaf=n.left==-1 && n.right==-1;
                if(!leaf && (n.left<=j || n.right<=j || n.left>=count || n.right>=count || n.feature<0 || n.feature>=int(NF)))
                    throw std::runtime_error("invalid tree topology");
            }
            trees.push_back(std::move(tree));
        }
    }
    double score(const Features& x) const {
        for(float v:x) if(!std::isfinite(v)) throw std::runtime_error("nonfinite feature");
        double total=0;
        for(const auto& tree:trees) {
            int idx=0,depth=0;
            while(tree[idx].left!=-1) {
                const auto& n=tree[idx]; idx=(x[n.feature]<=n.threshold)?n.left:n.right; ++depth;
            }
            total += depth+correction(tree[idx].samples);
        }
        return std::pow(2.0,-total/(trees.size()*correction(max_samples)));
    }
};
using Clock=std::chrono::steady_clock;
class Detector {
    const Forest& model_; bool realtime_; Clock::time_point wall_=Clock::now();
    bool origin_set_=false; uint64_t origin_=0; unsigned bad_=0,good_=0;
    std::string state_="HEALTHY";
public:
    uint64_t rx_drops=0,ignored=0;
    Detector(const Forest& m,bool rt):model_(m),realtime_(rt){}
    void emit(const Window& w) {
        if(!origin_set_) {origin_=w.start; origin_set_=true;}
        if(realtime_) std::this_thread::sleep_until(wall_+std::chrono::microseconds(w.start-origin_+WINDOW_US));
        auto before=Clock::now(); double score=w.count ? model_.score(w.x) : 0;
        double infer_us=std::chrono::duration<double,std::micro>(Clock::now()-before).count();
        bool hard=w.unknown>0 || w.x[0]>1800;
        bool abnormal=hard || score>model_.threshold;
        std::string reason= w.unknown ? "unknown_id" : w.x[0]>1800 ? "possible_flooding" : abnormal ? "ml_anomaly" : "normal";
        if(w.count==0) {state_="NO_DATA";bad_=good_=0;reason="no_frames";}
        else if(abnormal) {
            ++bad_;good_=0;
            if(hard || bad_>=2 || state_=="ALERT") state_="ALERT"; else state_="SUSPECT";
        } else {
            bad_=0;++good_;
            if(state_!="ALERT" || good_>=5) state_="HEALTHY";
        }
        std::cout<<std::setprecision(10)<<"{\"t_ms\":"<<w.start/1000
            <<",\"window_end_ms\":"<<(w.start+WINDOW_US)/1000
            <<",\"frames\":"<<w.count<<",\"fps\":"<<w.x[0]<<",\"score\":"<<score
            <<",\"threshold\":"<<model_.threshold<<",\"state\":\""<<state_
            <<"\",\"reason\":\""<<reason<<"\",\"unknown_frames\":"<<w.unknown
            <<",\"inference_us\":"<<infer_us<<",\"rx_drops\":"<<rx_drops
            <<",\"ignored_frames\":"<<ignored<<"}"<<std::endl;
    }
};
#ifdef __linux__
volatile std::sig_atomic_t running=1;
void stop(int) {running=0;}
void capture(const std::string& iface, const Forest& model) {
    unsigned index=if_nametoindex(iface.c_str()); if(!index) throw std::runtime_error("CAN interface not found");
    int fd=socket(PF_CAN,SOCK_RAW,CAN_RAW); if(fd<0) throw std::runtime_error("socket failed");
    struct Guard {int fd;~Guard(){close(fd);}} guard{fd};
    int one=1,buf=1024*1024;
    if(setsockopt(fd,SOL_SOCKET,SO_RXQ_OVFL,&one,sizeof(one))<0 ||
       setsockopt(fd,SOL_SOCKET,SO_RCVBUF,&buf,sizeof(buf))<0)
        throw std::runtime_error("receive buffer options failed");
    // Receive errors too; they count as degraded/ignored input, not payload features.
    can_err_mask_t errors=CAN_ERR_MASK;
    if(setsockopt(fd,SOL_CAN_RAW,CAN_RAW_ERR_FILTER,&errors,sizeof(errors))<0)
        throw std::runtime_error("error filter failed");
    sockaddr_can addr{}; addr.can_family=AF_CAN;addr.can_ifindex=int(index);
    if(bind(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))<0) throw std::runtime_error("bind failed");
    std::signal(SIGINT,stop);std::signal(SIGTERM,stop);
    Detector detector(model,false);Extractor extractor(model.whitelist);auto origin=Clock::now();
    auto emit=[&](const Window& w){detector.emit(w);};
    auto timestamp=[&](){return uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(Clock::now()-origin).count());};
    while(running) {
        pollfd p{fd,POLLIN,0};int ready=poll(&p,1,20);
        if(ready<0) {if(errno==EINTR) continue;throw std::runtime_error("CAN poll failed");}
        if(p.revents&(POLLERR|POLLHUP|POLLNVAL)) throw std::runtime_error("CAN interface error/disconnected");
        if(!ready) {extractor.advance(timestamp(),emit);continue;}
        can_frame raw{}; char control[CMSG_SPACE(sizeof(uint32_t))]{};
        iovec io{&raw,sizeof(raw)};msghdr msg{};msg.msg_iov=&io;msg.msg_iovlen=1;
        msg.msg_control=control;msg.msg_controllen=sizeof(control);
        auto n=recvmsg(fd,&msg,0);
        if(n<0) {if(errno==EINTR)continue;throw std::runtime_error("CAN receive failed");}
        for(auto c=CMSG_FIRSTHDR(&msg);c;c=CMSG_NXTHDR(&msg,c)) {
            if(c->cmsg_level==SOL_SOCKET && c->cmsg_type==SO_RXQ_OVFL && c->cmsg_len>=CMSG_LEN(sizeof(uint32_t))) {
                uint32_t drops;std::memcpy(&drops,CMSG_DATA(c),sizeof(drops));detector.rx_drops=drops;
            }
        }
        if(n!=CAN_MTU || raw.len>8 || raw.can_id&(CAN_EFF_FLAG|CAN_RTR_FLAG|CAN_ERR_FLAG)) {
            ++detector.ignored;continue;
        }
        Frame f{timestamp(),raw.can_id&CAN_SFF_MASK,{raw.data,raw.data+raw.len}};
        extractor.push(f,emit);
    }
    // Monitoring path contains no CAN send/write API.
}
#endif
int main(int argc,char** argv) {
    try {
        if(argc<4) throw std::runtime_error("usage: ai-vids features INPUT.csv OUTPUT.csv | score MODEL.forest FEATURES.csv | replay INPUT.csv MODEL.forest [--realtime] | capture IFACE MODEL.forest");
        std::string mode=argv[1];
        if(mode=="features") {
            std::set<uint32_t> ids;Extractor extractor(ids);std::ofstream out(argv[3]);
            if(!out) throw std::runtime_error("cannot open features output");
            out<<"t_us,fps,unique_ids,id_entropy,max_id_share,byte_mean,byte_std,bit_flip_mean,same_id_iat_ms\n";
            read_csv(argv[2],[&](const Frame& f){extractor.push(f,[&](const Window& w){
                out<<w.start<<std::setprecision(10);for(float x:w.x)out<<','<<x;out<<'\n';
            });});
        } else if(mode=="score") {
            Forest m(argv[2]);std::ifstream in(argv[3]);if(!in)throw std::runtime_error("cannot open feature file");
            std::string line;std::getline(in,line);
            while(std::getline(in,line)) {
                std::istringstream ss(line);std::string v;std::getline(ss,v,',');Features x;
                for(auto& f:x) {if(!std::getline(ss,v,','))throw std::runtime_error("feature row too short");f=std::stof(v);}
                std::cout<<std::setprecision(17)<<m.score(x)<<'\n';
            }
        } else if(mode=="replay") {
            Forest m(argv[3]);Extractor e(m.whitelist);Detector d(m,argc==5 && std::string(argv[4])=="--realtime");
            read_csv(argv[2],[&](const Frame& f){e.push(f,[&](const Window& w){d.emit(w);});});
        } else if(mode=="capture") {
#ifdef __linux__
            Forest m(argv[3]);capture(argv[2],m);
#else
            throw std::runtime_error("SocketCAN capture requires Linux; use replay on Windows");
#endif
        } else throw std::runtime_error("unknown command");
        return 0;
    } catch(const std::exception& e) {std::cerr<<"ai-vids: "<<e.what()<<'\n';return 1;}
}
