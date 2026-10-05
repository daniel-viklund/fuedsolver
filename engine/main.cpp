#include "vendor/json.hpp"
#include <array>
#include <chrono>
#include <codecvt>
#include <fstream>
#include <iostream>
#include <locale>
#include <set>
#include <string>
#include <vector>

using json = nlohmann::json;
using Word = std::u32string;
const Word alphabet = U"ABCDEFGHIJKLMNOPRSTUVXYZÅÄÖ";
const std::array<int,27> points = {1,3,8,1,1,3,2,3,1,7,3,2,3,1,2,4,1,1,1,4,3,8,7,8,4,4,4};
Word decode(const std::string& s) { return std::wstring_convert<std::codecvt_utf8<char32_t>,char32_t>{}.from_bytes(s); }
std::string encode(const Word& s) { return std::wstring_convert<std::codecvt_utf8<char32_t>,char32_t>{}.to_bytes(s); }
char32_t upper(char32_t c) { if(c>=U'a'&&c<=U'z') return c-32; if(c==U'å'||c==U'ä'||c==U'ö') return c-32; return c; }
int letter(char32_t c) { auto p=alphabet.find(upper(c)); return p==Word::npos ? -1 : int(p); }
bool inside(int r,int c) { return r>=0&&r<15&&c>=0&&c<15; }
struct Node { std::array<int,27> next{}; bool end=false; };
struct Tile { int r,c,l; bool blank; };
struct Cross { unsigned mask=(1u<<27)-1; int score=0; bool adjacent=false; };

class Solver {
    std::vector<Node> trie{1};
    int board[15][15], value[15][15]{}, lm[15][15], wm[15][15];
    std::array<int,27> rack{};
    int blanks=0, dictionary_size=0;
    bool empty=true;
    Cross crosses[2][15][15];
    std::vector<Tile> placed;
    std::vector<json> moves;
    std::set<std::string> seen;
    Word word;
    bool contains(const Word& w) const {
        int n=0;
        for(auto c:w) { int l=letter(c); if(l<0||!trie[n].next[l]) return false; n=trie[n].next[l]; }
        return trie[n].end;
    }
    void search(int r,int c,int sr,int sc,int dir,int node,int sum,int mult,int cross_score,bool connected) {
        int dr=dir, dc=1-dir;
        bool in=inside(r,c);
        if(trie[node].end && word.size()>=2 && !placed.empty() && connected && (!in||board[r][c]<0)) {
            json tiles=json::array(); std::string key;
            for(const auto& t:placed) { tiles.push_back({{"row",t.r},{"col",t.c},{"letter",encode(Word(1,alphabet[t.l]))},{"blank",t.blank}}); key+=std::to_string(t.r)+","+std::to_string(t.c)+","+std::to_string(t.l)+","+std::to_string(t.blank)+";"; }
            if(seen.insert(key).second) moves.push_back({{"word",encode(word)},{"row",sr},{"col",sc},{"direction",dir?"vertical":"horizontal"},{"score",sum*mult+cross_score+(placed.size()==7?40:0)},{"tiles",tiles},{"bingo",placed.size()==7}});
        }
        if(!in) return;
        int l=board[r][c];
        if(l>=0) {
            int next=trie[node].next[l]; if(!next) return;
            word.push_back(alphabet[l]); search(r+dr,c+dc,sr,sc,dir,next,sum+value[r][c],mult,cross_score,true); word.pop_back(); return;
        }
        if(placed.size()==7) return;
        const auto& cross=crosses[dir][r][c];
        for(int a=0;a<27;++a) {
            int next=trie[node].next[a]; if(!next || !(cross.mask&(1u<<a))) continue;
            for(int blank=0;blank<=1;++blank) {
                if(blank ? !blanks : !rack[a]) continue;
                if(blank) --blanks; else --rack[a];
                int v=blank?0:points[a]*lm[r][c];
                placed.push_back({r,c,a,bool(blank)}); word.push_back(alphabet[a]);
                search(r+dr,c+dc,sr,sc,dir,next,sum+v,mult*wm[r][c],cross_score+(cross.adjacent?(cross.score+v)*wm[r][c]:0),connected||cross.adjacent||(empty&&r==7&&c==7));
                word.pop_back(); placed.pop_back(); if(blank) ++blanks; else ++rack[a];
            }
        }
    }
public:
    Solver(const json& p,const std::string& dictionary) {
        std::ifstream file(dictionary); if(!file) throw std::runtime_error("Cannot open dictionary: "+dictionary);
        std::string line;
        while(std::getline(file,line)) {
            if(!line.empty()&&line.back()=='\r') line.pop_back();
            Word w=decode(line); if(w.size()<2||w.size()>15) continue;
            if(std::any_of(w.begin(),w.end(),[](char32_t c){return letter(c)<0;})) continue;
            int n=0; for(auto c:w) { int a=letter(c); if(!trie[n].next[a]) { int next=int(trie.size()); trie[n].next[a]=next; trie.emplace_back(); } n=trie[n].next[a]; }
            if(!trie[n].end) { trie[n].end=true; ++dictionary_size; }
        }
        if(!dictionary_size) throw std::runtime_error("Dictionary contains no valid Swedish words");
        if(!p.at("board").is_array()||p.at("board").size()!=15) throw std::runtime_error("Board must have 15 rows");
        const std::array<std::string,15> standard={"T...W..d..W...T",".d...T...T...d.","..w...d.d...w..","...T...w...T...","W...w.d.d.w...W",".T...T...T...T.","..d.d.....d.d..","d..w.......w..d","..d.d.....d.d..",".T...T...T...T.","W...w.d.d.w...W","...T...w...T...","..w...d.d...w..",".d...T...T...d.","T...W..d..W...T"};
        if(p.contains("bonuses")&&(!p["bonuses"].is_array()||p["bonuses"].size()!=15)) throw std::runtime_error("Bonuses must have 15 rows");
        for(int r=0;r<15;++r) {
            Word row=decode(p["board"][r].get<std::string>()); if(row.size()!=15) throw std::runtime_error("Each board row must have 15 characters");
            if(p.contains("bonuses")&&(!p["bonuses"][r].is_array()||p["bonuses"][r].size()!=15)) throw std::runtime_error("Each bonus row must have 15 cells");
            for(int c=0;c<15;++c) {
                board[r][c]=letter(row[c]); if(board[r][c]<0&&row[c]!=U'.') throw std::runtime_error("Invalid board letter");
                if(board[r][c]>=0) { empty=false; value[r][c]=row[c]==upper(row[c])?points[board[r][c]]:0; }
                char b=standard[r][c]; std::string bonus=b=='T'?"TL":b=='W'?"TW":b=='d'?"DL":b=='w'?"DW":"";
                if(p.contains("bonuses")) bonus=p["bonuses"][r][c].get<std::string>();
                if(bonus!=""&&bonus!="DL"&&bonus!="TL"&&bonus!="DW"&&bonus!="TW") throw std::runtime_error("Invalid bonus square");
                lm[r][c]=bonus=="DL"?2:bonus=="TL"?3:1; wm[r][c]=bonus=="DW"?2:bonus=="TW"?3:1;
            }
        }
        Word hand=decode(p.at("rack").get<std::string>()); if(hand.empty()||hand.size()>7) throw std::runtime_error("Rack must contain 1 to 7 tiles");
        for(auto c:hand) { if(c==U'?') ++blanks; else {int l=letter(c); if(l<0) throw std::runtime_error("Invalid rack letter (use ? for blanks)"); ++rack[l];} }
        for(int d=0;d<2;++d) for(int r=0;r<15;++r) for(int c=0;c<15;++c) {
            if(board[r][c]>=0) continue;
            int dr=1-d, dc=d; Word pre,post; auto& cross=crosses[d][r][c];
            for(int y=r-dr,x=c-dc;inside(y,x)&&board[y][x]>=0;y-=dr,x-=dc) {pre.insert(pre.begin(),alphabet[board[y][x]]); cross.score+=value[y][x];}
            for(int y=r+dr,x=c+dc;inside(y,x)&&board[y][x]>=0;y+=dr,x+=dc) {post.push_back(alphabet[board[y][x]]); cross.score+=value[y][x];}
            cross.adjacent=!pre.empty()||!post.empty();
            if(cross.adjacent) {cross.mask=0; for(int a=0;a<27;++a) if(contains(pre+Word(1,alphabet[a])+post)) cross.mask|=1u<<a;}
        }
    }
    json solve(int limit) {
        auto start=std::chrono::steady_clock::now();
        for(int d=0;d<2;++d) for(int r=0;r<15;++r) for(int c=0;c<15;++c) {
            if(inside(r-d,c-(1-d))&&board[r-d][c-(1-d)]>=0) continue;
            search(r,c,r,c,d,0,0,1,0,false);
        }
        std::sort(moves.begin(),moves.end(),[](const json& a,const json& b){if(a["score"]!=b["score"]) return a["score"]>b["score"]; if(a["word"]!=b["word"]) return a["word"]<b["word"]; return a.dump()<b.dump();});
        size_t total=moves.size(); if(moves.size()>size_t(limit)) moves.resize(limit);
        auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        return {{"moves",moves},{"total_moves",total},{"search_ms",ms},{"dictionary_words",dictionary_size}};
    }
};
int main(int argc,char** argv) {
    try {
        std::string dictionary="data/swedish.txt",position; int limit=20;
        for(int i=1;i<argc;++i) {
            std::string arg=argv[i];
            if(arg=="--help") {std::cout<<"feudsolver --dictionary words.txt [--position position.json] [--limit 20]\nReads JSON from stdin when --position is omitted; writes JSON to stdout.\n"; return 0;}
            if(i+1>=argc) throw std::runtime_error("Missing argument value");
            if(arg=="--dictionary") dictionary=argv[++i]; else if(arg=="--position") position=argv[++i]; else if(arg=="--limit") limit=std::stoi(argv[++i]); else throw std::runtime_error("Unknown flag: "+arg);
        }
        if(limit<1||limit>1000) throw std::runtime_error("Limit must be 1 to 1000");
        json p; if(position.empty()) std::cin>>p; else {std::ifstream f(position); if(!f) throw std::runtime_error("Cannot open position"); f>>p;}
        std::cout<<Solver(p,dictionary).solve(limit).dump()<<'\n';
    } catch(const std::exception& e) {std::cerr<<json({{"error",e.what()}}).dump()<<'\n'; return 1;}
}
