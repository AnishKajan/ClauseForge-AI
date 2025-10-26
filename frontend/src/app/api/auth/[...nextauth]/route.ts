import NextAuth from "next-auth"
import AzureAD from "next-auth/providers/azure-ad"

const handler = NextAuth({
  secret: process.env.NEXTAUTH_SECRET,
  session: { strategy: "jwt" },
  providers: [
    AzureAD({
      clientId: process.env.AZURE_AD_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
      tenantId: process.env.AZURE_AD_TENANT_ID!,
      authorization: { params: { scope: "openid profile email" } },
    }),
  ],
  callbacks: {
    async signIn({ profile }) {
      // allow only .edu emails; remove this block if tenant restriction is enough
      return profile?.email?.toLowerCase().endsWith(".edu") ?? false
    },
    async jwt({ token, account }) {
      if (account?.id_token) token.idToken = account.id_token
      return token
    },
    async session({ session, token }) {
      if (token?.idToken) (session as any).idToken = token.idToken as string
      return session
    },
  },
})

export { handler as GET, handler as POST }